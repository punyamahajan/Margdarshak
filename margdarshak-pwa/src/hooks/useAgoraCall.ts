import { useCallback, useEffect, useRef, useState } from "react";
import AgoraRTC, {
  type IAgoraRTCClient,
  type IAgoraRTCRemoteUser,
  type IMicrophoneAudioTrack,
  type IRemoteAudioTrack
} from "agora-rtc-sdk-ng";
import type { VoiceSession } from "../services/apiClient";
import AgoraRTM, { type RTMClient } from "agora-rtm";
import {
  AgoraVoiceAI,
  AgoraVoiceAIEvents,
  TranscriptHelperMode,
  TurnStatus,
  type TranscriptHelperItem
} from "agora-agent-client-toolkit";

export type CallState = "Connecting" | "Listening" | "Speaking" | "Call ended";

type AudioLevels = {
  local: number;
  remote: number;
};

export type LiveTranscriptTurn = {
  key: string;
  speaker: "student" | "agent";
  content: string;
  final: boolean;
  source: "agora" | "browser";
};

type BrowserSpeechResult = {
  isFinal: boolean;
  0: { transcript: string };
};

type BrowserSpeechEvent = {
  resultIndex: number;
  results: ArrayLike<BrowserSpeechResult>;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: BrowserSpeechEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start(): void;
  stop(): void;
};

type BrowserSpeechConstructor = new () => BrowserSpeechRecognition;

export function useAgoraCall(session: VoiceSession | null) {
  const [callState, setCallState] = useState<CallState>("Connecting");
  const [audioLevels, setAudioLevels] = useState<AudioLevels>({ local: 0, remote: 0 });
  const [error, setError] = useState<string | null>(null);
  const [microphoneReady, setMicrophoneReady] = useState(false);
  const [doneSpeaking, setDoneSpeaking] = useState(false);
  const [transcript, setTranscript] = useState<LiveTranscriptTurn[]>([]);
  const clientRef = useRef<IAgoraRTCClient | null>(null);
  const localTrackRef = useRef<IMicrophoneAudioTrack | null>(null);
  const remoteTrackRef = useRef<IRemoteAudioTrack | null>(null);
  const connectedRef = useRef(false);
  const rtmRef = useRef<RTMClient | null>(null);
  const speechRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const doneSpeakingRef = useRef(false);
  const cleanupRef = useRef<() => Promise<void>>(async () => undefined);

  useEffect(() => {
    if (!session) return;
    let disposed = false;
    const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
    clientRef.current = client;

    const handleUserPublished = async (
      user: IAgoraRTCRemoteUser,
      mediaType: "audio" | "video" | "datachannel"
    ) => {
      if (mediaType !== "audio") return;
      await client.subscribe(user, mediaType);
      if (disposed || !user.audioTrack) return;
      remoteTrackRef.current = user.audioTrack;
      user.audioTrack.play();
    };

    const handleUserUnpublished = (
      user: IAgoraRTCRemoteUser,
      mediaType: "audio" | "video" | "datachannel"
    ) => {
      if (mediaType === "audio" && remoteTrackRef.current === user.audioTrack) {
        remoteTrackRef.current = null;
      }
    };

    client.on("user-published", handleUserPublished);
    client.on("user-unpublished", handleUserUnpublished);

    const cleanup = async () => {
      localTrackRef.current?.stop();
      localTrackRef.current?.close();
      localTrackRef.current = null;
      setMicrophoneReady(false);
      setDoneSpeaking(false);
      doneSpeakingRef.current = false;
      remoteTrackRef.current?.stop();
      remoteTrackRef.current = null;
      speechRecognitionRef.current?.stop();
      speechRecognitionRef.current = null;
      if (rtmRef.current) {
        try {
          await rtmRef.current.logout();
        } catch {
          // It may already be disconnected during teardown.
        }
        rtmRef.current = null;
      }
      client.removeAllListeners();
      if (client.connectionState !== "DISCONNECTED") await client.leave();
      connectedRef.current = false;
      clientRef.current = null;
      setAudioLevels({ local: 0, remote: 0 });
    };
    cleanupRef.current = cleanup;

    void (async () => {
      try {
        setCallState("Connecting");
        await client.join(
          session.agora_app_id,
          session.channel_name,
          session.rtc_token,
          session.uid
        );
        const microphoneTrack = await AgoraRTC.createMicrophoneAudioTrack();
        if (disposed) {
          microphoneTrack.close();
          return;
        }
        localTrackRef.current = microphoneTrack;
        await client.publish(microphoneTrack);
        let rtmClient: RTMClient | null = null;
        try {
          rtmClient = new AgoraRTM.RTM(
            session.agora_app_id,
            String(session.uid),
            { useStringUserId: false }
          );
          await rtmClient.login({ token: session.rtm_token });
          await rtmClient.subscribe(session.channel_name);
          rtmRef.current = rtmClient;
        } catch {
          // Transcript delivery can also arrive over the RTC stream channel.
          rtmClient = null;
        }
        const ai = await AgoraVoiceAI.init({
          rtcEngine: client,
          ...(rtmClient ? { rtmConfig: { rtmEngine: rtmClient } } : {}),
          renderMode: TranscriptHelperMode.TEXT,
          enableLog: false
        });
        ai.on(
          AgoraVoiceAIEvents.TRANSCRIPT_UPDATED,
          (items: TranscriptHelperItem<unknown>[]) => {
            if (disposed) return;
            const agoraTurns: LiveTranscriptTurn[] = items
                .filter((item) => typeof item.text === "string" && item.text.trim())
                .map((item) => ({
                  key: String(item.turn_id),
                  speaker: item.uid === "0" ? "student" : "agent",
                  content: String(item.text).trim(),
                  final: item.status !== TurnStatus.IN_PROGRESS,
                  source: "agora"
                }));
            setTranscript((current) => [
              ...current.filter((item) => item.source === "browser"),
              ...agoraTurns
            ]);
          }
        );
        ai.subscribeMessage(session.channel_name);
        const speechWindow = window as typeof window & {
          SpeechRecognition?: BrowserSpeechConstructor;
          webkitSpeechRecognition?: BrowserSpeechConstructor;
        };
        const SpeechRecognition =
          speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
        if (SpeechRecognition) {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = "en-IN";
          recognition.onresult = (event) => {
            const browserTurns: LiveTranscriptTurn[] = [];
            for (let index = event.resultIndex; index < event.results.length; index += 1) {
              const result = event.results[index];
              const content = result[0]?.transcript.trim();
              if (!content) continue;
              browserTurns.push({
                key: `browser-${Date.now()}-${index}`,
                speaker: "student",
                content,
                final: result.isFinal,
                source: "browser"
              });
            }
            if (browserTurns.length) {
              setTranscript((current) => [
                ...current.filter(
                  (item) => item.source !== "browser" || item.final
                ),
                ...browserTurns
              ]);
            }
          };
          recognition.onend = () => {
            if (!disposed && speechRecognitionRef.current === recognition) {
              try { recognition.start(); } catch { /* already restarting */ }
            }
          };
          recognition.onerror = () => undefined;
          speechRecognitionRef.current = recognition;
          try { recognition.start(); } catch { /* browser denied speech recognition */ }
        }
        connectedRef.current = true;
        setMicrophoneReady(true);
        setCallState("Listening");
      } catch (cause) {
        if (!disposed) {
          setError(cause instanceof Error ? cause.message : String(cause));
          setCallState("Call ended");
        }
        await cleanup();
      }
    })();

    const levelTimer = window.setInterval(() => {
      const local = doneSpeakingRef.current ? 0 : localTrackRef.current?.getVolumeLevel() ?? 0;
      const remote = remoteTrackRef.current?.getVolumeLevel() ?? 0;
      setAudioLevels({ local, remote });
      if (connectedRef.current) {
        setCallState(local > 0.08 ? "Speaking" : "Listening");
      }
    }, 120);

    return () => {
      disposed = true;
      window.clearInterval(levelTimer);
      void cleanup();
      try {
        const ai = AgoraVoiceAI.getInstance();
        ai.unsubscribe();
        ai.destroy();
      } catch {
        // The toolkit may not have initialized if RTC setup failed.
      }
    };
  }, [session]);

  const finishSpeaking = useCallback(async () => {
    if (!localTrackRef.current) return;
    await localTrackRef.current.setMuted(true);
    doneSpeakingRef.current = true;
    setDoneSpeaking(true);
    setCallState("Listening");
  }, []);

  const resumeSpeaking = useCallback(async () => {
    if (!localTrackRef.current) return;
    await localTrackRef.current.setMuted(false);
    doneSpeakingRef.current = false;
    setDoneSpeaking(false);
  }, []);

  const leave = useCallback(async () => {
    await cleanupRef.current();
    setCallState("Call ended");
  }, []);

  return {
    callState,
    audioLevels,
    error,
    leave,
    microphoneReady,
    doneSpeaking,
    finishSpeaking,
    resumeSpeaking,
    transcript
  };
}
