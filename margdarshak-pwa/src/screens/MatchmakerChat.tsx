import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { apiClient, createMatchmakerSocket } from "../services/apiClient";

type AnonymousMessage = {
  sender: "self" | "peer" | "system" | "demo";
  content: string;
  sent_at?: string | null;
};

type MatchmakerChatProps = {
  bridgeId: string;
  onBack: () => void;
};

type ConsentState = "idle" | "working" | "waiting" | "complete";
const STUDENT_ID = import.meta.env.VITE_STUDENT_ID as string | undefined;
const DEMO_INTRO: AnonymousMessage = {
  sender: "demo",
  content: "Hello! I’m your demo match. I’m interested in Python, backend development, and placement preparation. What skills are you working on?",
  sent_at: "local-intro",
};

function localDemoReply(content: string): string {
  const normalized = content.toLowerCase();
  if (/\b(hi|hello|hey)\b/.test(normalized)) {
    return "Hi! Nice to meet you anonymously. What skill or project are you focusing on right now?";
  }
  if (/python|backend|fastapi|coding|development/.test(normalized)) {
    return "That’s close to what I’m learning too. Are you building a project with it or preparing for interviews?";
  }
  if (/placement|interview|job|career/.test(normalized)) {
    return "I’m preparing for placements as well. Which part would you like to compare notes on: aptitude, projects, or interviews?";
  }
  return "That sounds interesting. What have you learned so far, and what part feels most difficult?";
}

function remainingLabel(expiresAt: string | null, now: number): string {
  if (!expiresAt) return "48h remaining";
  const remaining = Math.max(0, new Date(expiresAt).getTime() - now);
  const hours = Math.floor(remaining / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  return remaining === 0 ? "Bridge expired" : `${hours}h ${minutes}m remaining`;
}

export function MatchmakerChat({ bridgeId, onBack }: MatchmakerChatProps) {
  const [messages, setMessages] = useState<AnonymousMessage[]>([DEMO_INTRO]);
  const [draft, setDraft] = useState("");
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const [connection, setConnection] = useState("Connecting");
  const [socketReady, setSocketReady] = useState(false);
  const [sendStatus, setSendStatus] = useState<string | null>(null);
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
    let disposed = false;
    let retryTimer: number | null = null;
    const connect = () => {
      if (disposed) return;
      setConnection("Connecting");
      const socket = createMatchmakerSocket(bridgeId, STUDENT_ID);
      socketRef.current = socket;
      socket.addEventListener("open", () => {
        setSocketReady(true);
        setSendStatus(null);
        setConnection("Anonymous bridge open · demo peer available");
      });
      socket.addEventListener("close", () => {
        setSocketReady(false);
        setConnection("Bridge offline · retrying");
        if (!disposed) retryTimer = window.setTimeout(connect, 2000);
      });
      socket.addEventListener("error", () => {
        setSocketReady(false);
        setConnection("Backend unavailable · retrying");
      });
      socket.addEventListener("message", (event) => {
        const payload = JSON.parse(String(event.data)) as
          | { type: "history"; messages: AnonymousMessage[] }
          | AnonymousMessage;
        if ("type" in payload && payload.type === "history") {
          setMessages((current) => {
            const localConversation = current.filter((message) => message.sent_at?.startsWith("local-"));
            const hasPeerOpening = payload.messages.some(
              (message) => message.sender === "peer" || message.sender === "demo"
            );
            const localWithoutIntro = hasPeerOpening
              ? localConversation.filter((message) => message.sent_at !== "local-intro")
              : localConversation;
            return [...payload.messages, ...localWithoutIntro];
          });
        }
        else if ("sender" in payload) setMessages((current) => [...current, payload]);
      });
    };
    connect();
    return () => {
      disposed = true;
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      socketRef.current?.close();
    };
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
    if (!content) return;
    setDraft("");
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(content);
      setSendStatus(null);
      return;
    }

    const timestamp = Date.now();
    setMessages((current) => [
      ...current,
      { sender: "self", content, sent_at: `local-${timestamp}-self` },
    ]);
    setSendStatus("Demo mode is active while the private bridge reconnects.");
    window.setTimeout(() => {
      setMessages((current) => [
        ...current,
        { sender: "demo", content: localDemoReply(content), sent_at: `local-${timestamp}-demo` },
      ]);
    }, 450);
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
            <span>{message.sender === "self" ? "You" : message.sender === "peer" ? "Match" : message.sender === "demo" ? "Demo match" : "Starting point"}</span>
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
        <textarea id="anonymous-message" rows={2} maxLength={4000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Say hi or share your skills—without your name or university…" disabled={expired} />
        <button type="submit" disabled={expired || !draft.trim()}>Send</button>
        {sendStatus || !socketReady ? (
          <p className="message-composer__status" role="status">
            {sendStatus ?? "Demo chat is ready while the private bridge connects…"}
          </p>
        ) : null}
      </form>
    </main>
  );
}
