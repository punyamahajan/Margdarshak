import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { apiClient, createMatchmakerSocket } from "../services/apiClient";

type AnonymousMessage = {
  sender: "self" | "peer" | "system";
  content: string;
  sent_at?: string | null;
};

type MatchmakerChatProps = {
  bridgeId: string;
  onBack: () => void;
};

type ConsentState = "idle" | "working" | "waiting" | "complete";
const STUDENT_ID = import.meta.env.VITE_STUDENT_ID as string | undefined;

function remainingLabel(expiresAt: string | null, now: number): string {
  if (!expiresAt) return "48h remaining";
  const remaining = Math.max(0, new Date(expiresAt).getTime() - now);
  const hours = Math.floor(remaining / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  return remaining === 0 ? "Bridge expired" : `${hours}h ${minutes}m remaining`;
}

export function MatchmakerChat({ bridgeId, onBack }: MatchmakerChatProps) {
  const [messages, setMessages] = useState<AnonymousMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const [connection, setConnection] = useState("Connecting");
  const [revealState, setRevealState] = useState<ConsentState>("idle");
  const [voiceState, setVoiceState] = useState<ConsentState>("idle");
  const [linkedinUrls, setLinkedinUrls] = useState<Array<string | null>>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const countdown = useMemo(() => remainingLabel(expiresAt, now), [expiresAt, now]);
  const expired = expiresAt ? new Date(expiresAt).getTime() <= now : false;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!STUDENT_ID) {
      setConnection("Missing VITE_STUDENT_ID");
      return;
    }
    void apiClient.getMatchBridge(bridgeId).then((bridge) => setExpiresAt(bridge.expires_at));
    const socket = createMatchmakerSocket(bridgeId, STUDENT_ID);
    socketRef.current = socket;
    socket.addEventListener("open", () => setConnection("Anonymous bridge open"));
    socket.addEventListener("close", () => setConnection("Bridge closed"));
    socket.addEventListener("error", () => setConnection("Connection interrupted"));
    socket.addEventListener("message", (event) => {
      const payload = JSON.parse(String(event.data)) as
        | { type: "history"; messages: AnonymousMessage[] }
        | AnonymousMessage;
      if ("type" in payload && payload.type === "history") setMessages(payload.messages);
      else if ("sender" in payload) setMessages((current) => [...current, payload]);
    });
    return () => socket.close();
  }, [bridgeId]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!STUDENT_ID || revealState !== "waiting") return;
    const check = async () => {
      try {
        const result = await apiClient.revealLinkedIn(bridgeId, STUDENT_ID);
        if (result.status === "revealed") {
          setRevealState("complete");
          setLinkedinUrls(result.linkedin_urls ?? []);
        }
      } catch {
        // Keep the consent state opaque while waiting.
      }
    };
    const timer = window.setInterval(check, 3000);
    return () => window.clearInterval(timer);
  }, [bridgeId, revealState]);

  useEffect(() => {
    if (voiceState !== "waiting") return;
    const check = async () => {
      try {
        const bridge = await apiClient.getMatchBridge(bridgeId);
        if (bridge.status === "upgraded_to_voice") setVoiceState("complete");
      } catch {
        // A lifecycle check reveals no individual consent activity.
      }
    };
    const timer = window.setInterval(check, 3000);
    return () => window.clearInterval(timer);
  }, [bridgeId, voiceState]);

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || socketRef.current?.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(content);
    setDraft("");
  }

  async function requestReveal() {
    if (!STUDENT_ID || revealState !== "idle") return;
    setRevealState("working");
    try {
      const result = await apiClient.revealLinkedIn(bridgeId, STUDENT_ID);
      if (result.status === "pending") setRevealState("waiting");
      else {
        setRevealState("complete");
        setLinkedinUrls(result.linkedin_urls ?? []);
      }
    } catch {
      setRevealState("idle");
    }
  }

  async function requestVoice() {
    if (!STUDENT_ID || voiceState !== "idle") return;
    setVoiceState("working");
    try {
      const result = await apiClient.upgradeMatchToVoice(bridgeId, STUDENT_ID);
      setVoiceState(result.status === "pending" ? "waiting" : "complete");
    } catch {
      setVoiceState("idle");
    }
  }

  const consentCopy = "Your choice is saved. This unlocks only if both people choose it.";

  return (
    <main className="matchmaker-chat">
      <header className="matchmaker-chat__header">
        <button className="text-button" type="button" onClick={onBack}>← Leave</button>
        <div><strong>Anonymous match</strong><span>{connection}</span></div>
        <time>{countdown}</time>
      </header>

      <section className="message-ledger" aria-live="polite">
        {messages.map((message, index) => (
          <article className="message-row" data-sender={message.sender} key={`${message.sent_at}-${index}`}>
            <span>{message.sender === "self" ? "You" : message.sender === "peer" ? "Match" : "Starting point"}</span>
            <p>{message.content}</p>
          </article>
        ))}
        <div ref={messageEndRef} />
      </section>

      <section className="consent-panel" aria-label="Mutual consent options">
        <button type="button" onClick={requestReveal} disabled={expired || revealState !== "idle"}>
          {revealState === "working"
            ? "Saving choice…"
            : revealState === "waiting"
              ? "Choice saved"
              : revealState === "complete"
                ? "LinkedIn revealed"
                : "Reveal LinkedIn"}
        </button>
        <button type="button" onClick={requestVoice} disabled={expired || voiceState !== "idle"}>
          {voiceState === "working"
            ? "Saving choice…"
            : voiceState === "waiting"
              ? "Choice saved"
              : voiceState === "complete"
                ? "Voice ready"
                : "Upgrade to voice call"}
        </button>
        {revealState === "waiting" || voiceState === "waiting" ? <p>{consentCopy}</p> : null}
        {linkedinUrls.length ? (
          <div className="revealed-links">
            {linkedinUrls.filter(Boolean).map((url) => <a href={url!} target="_blank" rel="noreferrer" key={url!}>Open LinkedIn profile</a>)}
          </div>
        ) : null}
        {voiceState === "complete" ? <p>Voice upgrade is ready for this bridge.</p> : null}
      </section>

      <form className="message-composer" onSubmit={sendMessage}>
        <label className="visually-hidden" htmlFor="anonymous-message">Message your match</label>
        <textarea id="anonymous-message" rows={2} maxLength={4000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write without sharing identifying details…" disabled={expired} />
        <button type="submit" disabled={expired || !draft.trim()}>Send</button>
      </form>
    </main>
  );
}
