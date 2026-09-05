import { useRef, useState } from "react";
import { apiClient } from "../services/apiClient";

type SpeechEvent = { results: ArrayLike<{ 0: { transcript: string } }> };
type SpeechRecognizer = { continuous: boolean; interimResults: boolean; lang: string; onresult: ((event: SpeechEvent) => void) | null; start(): void; stop(): void };
type SpeechConstructor = new () => SpeechRecognizer;

export function AdminVoiceDraft({ onTranscript }: { onTranscript: (value: string) => void }) {
  const [active, setActive] = useState(false); const [status, setStatus] = useState("");
  const rtc = useRef<{ leave(): Promise<void> } | null>(null); const mic = useRef<{ stop(): void; close(): void } | null>(null); const speech = useRef<SpeechRecognizer | null>(null);
  async function stop() { speech.current?.stop(); mic.current?.stop(); mic.current?.close(); await rtc.current?.leave(); speech.current=null;mic.current=null;rtc.current=null;setActive(false);setStatus("Voice notes captured. Review the draft before sending."); }
  async function start() { try { setStatus("Connecting to Agora…"); const session=await apiClient.startAdminAgoraSession(); const Agora=(await import("agora-rtc-sdk-ng")).default; const client=Agora.createClient({mode:"rtc",codec:"vp8"}); await client.join(session.app_id,session.channel_name,session.rtc_token,session.uid); const track=await Agora.createMicrophoneAudioTrack(); await client.publish(track);rtc.current=client;mic.current=track; const scope=window as typeof window & {SpeechRecognition?:SpeechConstructor;webkitSpeechRecognition?:SpeechConstructor}; const Constructor=scope.SpeechRecognition||scope.webkitSpeechRecognition; if(Constructor){const recognizer=new Constructor();recognizer.continuous=true;recognizer.interimResults=false;recognizer.lang="en-IN";recognizer.onresult=event=>onTranscript(Array.from(event.results).map(result=>result[0].transcript).join(" "));recognizer.start();speech.current=recognizer;setStatus("Listening… speak the student update.");}else setStatus("Agora is connected. Type notes because browser speech recognition is unavailable.");setActive(true); } catch { setStatus("Agora connection failed. You can still type and draft the update.");setActive(false); } }
  return <div className="admin-voice"><button type="button" onClick={()=>void(active?stop():start())}>{active?"■ Stop voice notes":"● Draft response with Agora"}</button>{status&&<small>{status}</small>}</div>;
}
