import { useEffect, useRef, useState } from "react";
import { Waveform } from "../components/Waveform";
import {
  SummaryCard,
  type SummaryCardContent,
  type SummaryCardVariant
} from "../components/SummaryCard";
import { useAgoraCall } from "../hooks/useAgoraCall";
import { apiClient, type VoiceSession } from "../services/apiClient";

type CallScreenProps = {
  onBack: () => void;
};

type LiveSummary = {
  title: string;
  content: SummaryCardContent[];
  variant: SummaryCardVariant;
};

const hiddenCaseFields = new Set(["policy", "last_transcript_chunk"]);

function isPopulated(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function readableLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function readableValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (Array.isArray(value)) return value.map(String).join(", ").slice(0, 96);
  if (typeof value === "object") return JSON.stringify(value).slice(0, 96);
  const rendered = String(value);
  return rendered.length > 96 ? `${rendered.slice(0, 93)}...` : rendered;
}

const STUDENT_ID = import.meta.env.VITE_STUDENT_ID as string | undefined;

export function CallScreen({ onBack }: CallScreenProps) {
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [agentNotice, setAgentNotice] = useState<string | null>(null);
  const [handoffName, setHandoffName] = useState<string | null>(null);
  const [ending, setEnding] = useState(false);
  const [liveSummary, setLiveSummary] = useState<LiveSummary | null>(null);
  const [summaryVisible, setSummaryVisible] = useState(false);
  const startedRef = useRef(false);
  const handoffSeenRef = useRef(false);
  const previousCaseCardRef = useRef<Record<string, unknown>>({});
  const previousTicketStatusRef = useRef<string | null>(null);
  const summaryTimerRef = useRef<number | null>(null);
  const {
    callState,
    audioLevels,
    error: agoraError,
    leave,
    microphoneReady,
    doneSpeaking,
    finishSpeaking,
    resumeSpeaking
  } = useAgoraCall(session);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    if (!STUDENT_ID) {
      setStartError("Set VITE_STUDENT_ID to an existing student UUID before starting a call.");
      return;
    }
    void apiClient
      .startVoiceSession(STUDENT_ID)
      .then((startedSession) => {
        setSession(startedSession);
        if (startedSession.agent.status === "start_pending") {
          setAgentNotice("Voice is connected, but the AI participant has not joined this call.");
        } else {
          setAgentNotice(null);
        }
      })
      .catch((cause: unknown) => {
        setStartError(cause instanceof Error ? cause.message : String(cause));
      });
  }, []);

  useEffect(() => {
    if (!session || callState === "Call ended") return;
    const checkHandoff = async () => {
      try {
        const status = await apiClient.getVoiceSessionStatus(session.session_id);
        if (status.escalated && status.poc_name && !handoffSeenRef.current) {
          handoffSeenRef.current = true;
          setHandoffName(status.poc_name);
          window.setTimeout(() => setHandoffName(null), 4500);
        }
      } catch {
        // Handoff polling is supplementary; RTC audio should continue uninterrupted.
      }
    };
    void checkHandoff();
    const timer = window.setInterval(checkHandoff, 2500);
    return () => window.clearInterval(timer);
  }, [session]);

  useEffect(() => {
    if (!session || callState === "Call ended") return;

    const checkCaseCard = async () => {
      try {
        const ticket = await apiClient.getTicket(session.ticket_id);
        const current = ticket.case_card ?? {};
        const previous = previousCaseCardRef.current;
        const changedKeys = Object.keys(current).filter(
          (key) =>
            !hiddenCaseFields.has(key) &&
            isPopulated(current[key]) &&
            JSON.stringify(current[key]) !== JSON.stringify(previous[key])
        );
        const escalationStarted =
          ticket.status === "escalated" && previousTicketStatusRef.current !== "escalated";

        previousCaseCardRef.current = current;
        previousTicketStatusRef.current = ticket.status;
        if (!changedKeys.length && !escalationStarted) return;

        const confirmationRequested = changedKeys.some(
          (key) => key.includes("confirmation") && current[key] !== false
        );
        const variant: SummaryCardVariant = escalationStarted
          ? "escalating"
          : confirmationRequested
            ? "confirmation-needed"
            : "info";
        const content: SummaryCardContent[] = changedKeys.slice(-5).map((key) => ({
          label: readableLabel(key),
          value: readableValue(current[key])
        }));
        if (escalationStarted && content.length < 5) {
          content.push("A coordinator is joining with this context.");
        }

        setLiveSummary({
          title:
            variant === "escalating"
              ? "Passing this along"
              : variant === "confirmation-needed"
                ? "Does this look right?"
                : "What I have so far",
          content,
          variant
        });
        setSummaryVisible(true);
        if (summaryTimerRef.current !== null) window.clearTimeout(summaryTimerRef.current);
        summaryTimerRef.current = window.setTimeout(() => setSummaryVisible(false), 6500);
      } catch {
        // Case-card polling must never interrupt the live audio experience.
      }
    };

    void checkCaseCard();
    const timer = window.setInterval(checkCaseCard, 1500);
    return () => {
      window.clearInterval(timer);
      if (summaryTimerRef.current !== null) window.clearTimeout(summaryTimerRef.current);
    };
  }, [session]);

  async function hangUp() {
    if (ending) return;
    setEnding(true);
    await leave();
    if (session) {
      try {
        await apiClient.endVoiceSession(session.session_id);
      } catch (cause) {
        setStartError(cause instanceof Error ? cause.message : String(cause));
      }
    }
    setEnding(false);
  }

  const visibleState = session
    ? doneSpeaking && callState !== "Call ended"
      ? "Waiting for reply"
      : callState
    : startError
      ? "Call ended"
      : "Connecting";

  return (
    <main className="call-screen">
      <header className="call-screen__header">
        <p className="wordmark">Margdarshak</p>
        <p className="call-screen__state" aria-live="polite">{visibleState}</p>
      </header>

      <section className="call-screen__voice" aria-label="Voice call">
        {handoffName ? (
          <div className="handoff-notice" role="status">
            <span>Human support</span>
            <strong>Connecting you to {handoffName}</strong>
          </div>
        ) : null}
        <Waveform
          active={visibleState === "Listening" || visibleState === "Speaking"}
          localLevel={audioLevels.local}
          remoteLevel={audioLevels.remote}
        />
        <p className="call-screen__hint">
          {visibleState === "Waiting for reply"
            ? "You are done speaking. Waiting for a reply."
            : visibleState === "Speaking"
              ? "Go ahead, I’m listening."
              : visibleState === "Listening"
                ? "You can speak whenever you’re ready."
              : visibleState === "Connecting"
                ? "Finding a quiet line for you…"
                : "Your call has ended."}
        </p>
        {startError || agoraError ? (
          <p className="call-screen__error" role="alert">{startError ?? agoraError}</p>
        ) : null}
        {agentNotice ? <p className="call-screen__notice" role="status">{agentNotice}</p> : null}
      </section>

      <footer className="call-screen__controls">
        {visibleState !== "Call ended" ? (
          <>
            <button
              className="turn-button"
              type="button"
              onClick={doneSpeaking ? resumeSpeaking : finishSpeaking}
              disabled={!microphoneReady || ending}
            >
              {doneSpeaking ? "Speak again" : "I’m done speaking"}
            </button>
            <button className="hang-up-button" type="button" onClick={hangUp} disabled={ending}>
              {ending ? "Ending…" : "Hang up"}
            </button>
          </>
        ) : (
          <button className="text-button" type="button" onClick={onBack}>Back home</button>
        )}
      </footer>
      <div className="call-screen__summary-layer">
        {liveSummary ? (
          <SummaryCard
            title={liveSummary.title}
            content={liveSummary.content}
            variant={liveSummary.variant}
            visible={summaryVisible}
          />
        ) : null}
      </div>
    </main>
  );
}
