import { useCallback, useEffect, useRef, useState } from "react";
import AgoraRTC, {
  type IAgoraRTCClient,
  type IAgoraRTCRemoteUser,
  type IMicrophoneAudioTrack,
  type IRemoteAudioTrack
} from "agora-rtc-sdk-ng";
import type { VoiceSession } from "../services/apiClient";

export type CallState = "Connecting" | "Listening" | "Speaking" | "Call ended";

type AudioLevels = {
  local: number;
  remote: number;
};

export function useAgoraCall(session: VoiceSession | null) {
  const [callState, setCallState] = useState<CallState>("Connecting");
  const [audioLevels, setAudioLevels] = useState<AudioLevels>({ local: 0, remote: 0 });
  const [error, setError] = useState<string | null>(null);
  const [microphoneReady, setMicrophoneReady] = useState(false);
  const [doneSpeaking, setDoneSpeaking] = useState(false);
  const clientRef = useRef<IAgoraRTCClient | null>(null);
  const localTrackRef = useRef<IMicrophoneAudioTrack | null>(null);
  const remoteTrackRef = useRef<IRemoteAudioTrack | null>(null);
  const connectedRef = useRef(false);
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
    resumeSpeaking
  };
}
