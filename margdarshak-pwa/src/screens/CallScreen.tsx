import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { Waveform } from "../components/Waveform";
import {
  SummaryCard,
  type SummaryCardContent,
  type SummaryCardVariant
} from "../components/SummaryCard";
import { RaisedTicketsCard } from "../components/RaisedTicketsCard";
import { ChatHistoryDrawer } from "../components/ChatHistoryDrawer";
import { useAgoraCall } from "../hooks/useAgoraCall";
import {
  apiClient,
  type ResourceRecommendation,
  type TicketWithCaseCard,
  type VoiceHistorySession,
  type VoiceSession
} from "../services/apiClient";

type CallScreenProps = {
  onBack: () => void;
};

type LiveSummary = {
  title: string;
  content: SummaryCardContent[];
  variant: SummaryCardVariant;
};

const hiddenCaseFields = new Set([
  "policy",
  "last_transcript_chunk",
  "routing_decision",
  "routing_score",
  "student_reply",
  "escalation",
  "parent_ticket_id",
  "latest_duplicate_ticket_id",
  "llm_provider",
]);

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

function isWebLink(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function linksInText(value: string): string[] {
  return (value.match(/https?:\/\/[^\s<>"']+/g) ?? [])
    .map((link) => link.replace(/[),.;!?]+$/, ""))
    .filter(isWebLink);
}

const STUDENT_ID = import.meta.env.VITE_STUDENT_ID as string | undefined;

export function CallScreen({ onBack }: CallScreenProps) {
  const { student, openProfileModal } = useAuth();
  const activeStudentId = student?.id ?? STUDENT_ID;

  const initials = student?.name
    ? student.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()
    : "ST";

  const [session, setSession] = useState<VoiceSession | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [agentNotice, setAgentNotice] = useState<string | null>(null);
  const [handoffName, setHandoffName] = useState<string | null>(null);
  const [escalated, setEscalated] = useState(false);
  const [ending, setEnding] = useState(false);
  const [liveSummary, setLiveSummary] = useState<LiveSummary | null>(null);
  const [summaryVisible, setSummaryVisible] = useState(false);
  const [caseCard, setCaseCard] = useState<Record<string, unknown>>({});
  const [resourceRecommendation, setResourceRecommendation] = useState<ResourceRecommendation | null>(null);
  const [linkTopic, setLinkTopic] = useState("");
  const [linkRequestBusy, setLinkRequestBusy] = useState(false);
  const [linkRequestError, setLinkRequestError] = useState<string | null>(null);
  const [earlierSessions, setEarlierSessions] = useState<VoiceHistorySession[]>([]);
  const [raisedTickets, setRaisedTickets] = useState<TicketWithCaseCard[]>([]);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [copiedLink, setCopiedLink] = useState<string | null>(null);
  const startedRef = useRef(false);
  const handoffSeenRef = useRef(false);
  const previousCaseCardRef = useRef<Record<string, unknown>>({});
  const previousTicketStatusRef = useRef<string | null>(null);
  const summaryTimerRef = useRef<number | null>(null);
  const persistedTurnsRef = useRef(new Set<string>());
  const persistedContentRef = useRef(new Set<string>());
  const {
    callState,
    audioLevels,
    error: agoraError,
    leave,
    microphoneReady,
    doneSpeaking,
    finishSpeaking,
    resumeSpeaking,
    transcript
  } = useAgoraCall(session);
  const resourceRequestDetected = caseCard.request_type === "learning_resource";

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    if (!activeStudentId) {
      setStartError("Please sign in or set VITE_STUDENT_ID before starting a call.");
      return;
    }
    void apiClient
      .startVoiceSession(activeStudentId)
      .then((startedSession) => {
        setSession(startedSession);
        void apiClient.getVoiceHistory(activeStudentId).then((history) => {
          setEarlierSessions(
            history.filter((item) => item.session_id !== startedSession.session_id)
          );
        }).catch(() => undefined);
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
    if (!session) return;
    for (const turn of transcript) {
      const contentKey = `${turn.speaker}:${turn.content.toLowerCase().replace(/\s+/g, " ").trim()}`;
      if (
        !turn.final ||
        persistedTurnsRef.current.has(turn.key) ||
        persistedContentRef.current.has(contentKey)
      ) continue;
      persistedTurnsRef.current.add(turn.key);
      persistedContentRef.current.add(contentKey);
      void apiClient
        .ingestTranscript(session.session_id, {
          speaker: turn.speaker,
          content: turn.content
        })
        .catch(() => {
          persistedTurnsRef.current.delete(turn.key);
          persistedContentRef.current.delete(contentKey);
        });
    }
  }, [session, transcript]);

  useEffect(() => {
    if (!session || callState === "Call ended") return;
    const checkHandoff = async () => {
      try {
        const status = await apiClient.getVoiceSessionStatus(session.session_id);
        setEscalated(status.escalated);
        if (status.escalated && !handoffSeenRef.current) {
          handoffSeenRef.current = true;
          setHandoffName(status.poc_name ?? "the placement support team");
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
    if (!activeStudentId) return;
    const loadTickets = async () => {
      try {
        setRaisedTickets(await apiClient.listTickets({ studentId: activeStudentId }));
      } catch {
        // Ticket list is supplementary to the live call.
      }
    };
    void loadTickets();
    const timer = window.setInterval(loadTickets, 4000);
    return () => window.clearInterval(timer);
  }, [activeStudentId, session?.ticket_id, caseCard.routing_decision, caseCard.similar_count]);

  useEffect(() => {
    if (!session || resourceRecommendation || !resourceRequestDetected) return;
    const checkRecommendation = async () => {
      try {
        setResourceRecommendation(
          await apiClient.getResourceRecommendation(session.session_id)
        );
      } catch {
        try {
          setResourceRecommendation(
            await apiClient.ensureResourceRecommendation(session.session_id)
          );
        } catch {
          // The student may not have requested a resource yet.
        }
      }
    };
    void checkRecommendation();
  }, [
    session,
    resourceRecommendation,
    resourceRequestDetected,
    transcript.length,
    caseCard.recommended_resource,
  ]);

  useEffect(() => {
    if (!session || callState === "Call ended") return;

    const checkCaseCard = async () => {
      try {
        const ticket = await apiClient.getTicket(session.ticket_id);
        const current = ticket.case_card ?? {};
        setCaseCard(current);
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

  async function copyLink(link: string) {
    try {
      await navigator.clipboard.writeText(link);
      setCopiedLink(link);
      window.setTimeout(() => setCopiedLink((current) => current === link ? null : current), 1800);
    } catch {
      setStartError("Could not copy the link. You can still open it and copy it from the browser.");
    }
  }

  async function requestCourseLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const topic = linkTopic.trim();
    if (!session || !topic || linkRequestBusy) return;
    setLinkRequestBusy(true);
    setLinkRequestError(null);
    try {
      await apiClient.ingestTranscript(session.session_id, {
        speaker: "student",
        content: `I want a ${topic} course resource. Please attach the link.`,
      });
      setResourceRecommendation(
        await apiClient.ensureResourceRecommendation(session.session_id)
      );
      setLinkTopic("");
    } catch {
      setLinkRequestError("Try DSA, system design, web development, DBMS, or operating systems.");
    } finally {
      setLinkRequestBusy(false);
    }
  }

  const visibleState = session
    ? doneSpeaking && callState !== "Call ended"
      ? "Waiting for reply"
      : callState
    : startError
      ? "Call ended"
      : "Connecting";

  const sharedLinks = Array.from(new Set([
    ...(resourceRecommendation ? [resourceRecommendation.resource.url] : []),
    ...Object.values(caseCard).filter(isWebLink),
    ...transcript.flatMap((turn) => linksInText(turn.content)),
  ]));

  return (
    <main className="call-screen">
      <header className="call-screen__header">
        <div className="call-screen__brand-group">
          <button
            type="button"
            className="call-screen__back-btn"
            onClick={onBack}
            aria-label="Back to home"
          >
            ←
          </button>
          <p className="wordmark">Margdarshak</p>
        </div>
        <div className="call-screen__header-right">
          <p className="call-screen__state" aria-live="polite">{visibleState}</p>
          <button
            type="button"
            className="chat-history-nav-btn"
            onClick={() => setSidePanelOpen(true)}
            aria-label="Open Chat History side panel"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14H6v-2h6v2zm4-4H6v-2h10v2zm0-4H6V7h10v2z" />
            </svg>
            <span>Chat History</span>
            {earlierSessions.length ? (
              <span className="chat-history-count-badge">{earlierSessions.length}</span>
            ) : null}
          </button>
          {student && (
            <button
              type="button"
              className="nav-profile-btn nav-profile-btn--compact"
              onClick={openProfileModal}
              aria-label="Open Student Profile"
              title={`${student.name} · View & edit subjects`}
            >
              <span className="nav-profile-avatar" aria-hidden="true">{initials}</span>
            </button>
          )}
        </div>
      </header>

      <section className="call-screen__voice" aria-label="Voice call">
        {handoffName ? (
          <div className="handoff-notice" role="status">
            <span>Human support</span>
            <strong>Your urgent case is queued for {handoffName}</strong>
          </div>
        ) : null}
        {escalated || caseCard.routing_decision === "escalated" ? (
          <div className="urgent-support-card" role="status">
            <strong>
              {typeof caseCard.student_reply === "string" && caseCard.student_reply.trim()
                ? caseCard.student_reply
                : "Connecting to coordinator."}
            </strong>
            <span>Your case has been sent to the placement coordinator with the live context.</span>
          </div>
        ) : typeof caseCard.student_reply === "string" && caseCard.student_reply.trim() ? (
          <div className="urgent-support-card" role="status">
            <strong>{caseCard.student_reply}</strong>
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

        {/* Primary Call Controls: Positioned right below the chatbot and above the cards */}
        <div className="call-screen__controls call-screen__controls--primary">
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
        </div>
      </section>

      <section className="call-screen__details" aria-label="Conversation details">
        <article className="live-case-card">
          <p className="section-kicker">Live case card</p>
          <h2>What I know so far</h2>
          {Object.entries(caseCard).filter(([key, value]) =>
            !hiddenCaseFields.has(key) && isPopulated(value)
          ).length ? (
            <dl>
              {Object.entries(caseCard)
                .filter(([key, value]) => !hiddenCaseFields.has(key) && isPopulated(value))
                .map(([key, value]) => (
                  <div key={key}>
                    <dt>{readableLabel(key)}</dt>
                    <dd>
                      {isWebLink(value) ? (
                        <span className="case-card-link">
                          <a href={value} target="_blank" rel="noreferrer">Open course</a>
                          <button type="button" onClick={() => void copyLink(value)}>
                            {copiedLink === value ? "Copied" : "Copy link"}
                          </button>
                        </span>
                      ) : readableValue(value)}
                    </dd>
                  </div>
                ))}
            </dl>
          ) : <p className="empty-detail">Listening for useful details…</p>}
        </article>

        {/* Distinct Raised Tickets Card with visible highlight for reply status */}
        <RaisedTicketsCard tickets={raisedTickets} />

        <article className="shared-links-card">
          <p className="section-kicker">From your conversation</p>
          <h2>Links shared</h2>
          {sharedLinks.length ? (
            <div className="shared-links-list" aria-live="polite">
              {sharedLinks.map((link, index) => (
                <div className="shared-link" key={link}>
                  <div>
                    <strong>{resourceRecommendation?.resource.title ?? (caseCard.recommended_resource ? readableValue(caseCard.recommended_resource) : `Shared link ${index + 1}`)}</strong>
                    <span>{new URL(link).hostname.replace(/^www\./, "")}</span>
                  </div>
                  <a href={link} target="_blank" rel="noreferrer">Open</a>
                  <button type="button" onClick={() => void copyLink(link)}>
                    {copiedLink === link ? "Copied" : "Copy"}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="link-request-empty">
              <p className="empty-detail">Course and resource links from the AI will appear here automatically.</p>
              <form className="link-topic-form" onSubmit={requestCourseLink}>
                <label htmlFor="link-topic">Voice request missed? Enter only the course topic.</label>
                <div>
                  <input
                    id="link-topic"
                    value={linkTopic}
                    onChange={(event) => setLinkTopic(event.target.value)}
                    placeholder="e.g. system design"
                    maxLength={80}
                  />
                  <button type="submit" disabled={!session || !linkTopic.trim() || linkRequestBusy}>
                    {linkRequestBusy ? "Finding…" : "Get link"}
                  </button>
                </div>
                {linkRequestError ? <p role="alert">{linkRequestError}</p> : null}
              </form>
            </div>
          )}
        </article>
      </section>

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

      {/* Gemini/ChatGPT-style Chat History Side Panel Drawer */}
      <ChatHistoryDrawer
        isOpen={sidePanelOpen}
        onClose={() => setSidePanelOpen(false)}
        sessions={earlierSessions}
      />
    </main>
  );
}
