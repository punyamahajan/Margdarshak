import { useEffect, useRef, useState, type FormEvent } from "react";
import { Waveform } from "../components/Waveform";
import {
  SummaryCard,
  type SummaryCardContent,
  type SummaryCardVariant
} from "../components/SummaryCard";
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

function sessionTitle(history: VoiceHistorySession): string {
  const firstStudentTurn = history.turns.find((turn) => turn.speaker === "student");
  if (!firstStudentTurn) return "Voice guidance conversation";
  const title = firstStudentTurn.content.trim();
  return title.length > 56 ? `${title.slice(0, 53)}...` : title;
}

function sessionDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function ticketStatusTone(status: TicketWithCaseCard["status"]): string {
  if (status === "escalated") return "pending";
  if (status === "resolved") return "resolved";
  return "waiting";
}

function ticketHeadline(ticket: TicketWithCaseCard): string {
  const summary = ticket.issue_summary.trim();
  if (summary) {
    return summary.length > 72 ? `${summary.slice(0, 69)}...` : summary;
  }
  const cardSummary = ticket.case_card?.issue_summary;
  if (typeof cardSummary === "string" && cardSummary.trim()) {
    return cardSummary.length > 72 ? `${cardSummary.slice(0, 69)}...` : cardSummary;
  }
  return "Placement support ticket";
}

export function CallScreen({ onBack }: CallScreenProps) {
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
  const visibleRaisedTickets = raisedTickets.filter(
    (ticket) =>
      ticket.issue_summary.trim().length > 0 ||
      ticket.status === "escalated" ||
      ticket.parent_ticket_id !== null ||
      ticket.similar_count > 1
  );

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
        void apiClient.getVoiceHistory(STUDENT_ID).then((history) => {
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
    if (!STUDENT_ID) return;
    const loadTickets = async () => {
      try {
        setRaisedTickets(await apiClient.listTickets({ studentId: STUDENT_ID }));
      } catch {
        // Ticket list is supplementary to the live call.
      }
    };
    void loadTickets();
    const timer = window.setInterval(loadTickets, 4000);
    return () => window.clearInterval(timer);
  }, [session?.ticket_id, caseCard.routing_decision, caseCard.similar_count]);

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
        <p className="wordmark">Margdarshak</p>
        <p className="call-screen__state" aria-live="polite">{visibleState}</p>
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

          <div className="tickets-raised" aria-label="Tickets raised">
            <div className="tickets-raised__header">
              <p className="section-kicker">Tickets Raised</p>
              <span>{visibleRaisedTickets.length}</span>
            </div>
            {visibleRaisedTickets.length ? (
              <ul className="tickets-raised__list">
                {visibleRaisedTickets.map((ticket) => (
                  <li key={ticket.id} className="ticket-raised-item">
                    <div className="ticket-raised-item__top">
                      <strong>{ticketHeadline(ticket)}</strong>
                      <span
                        className={`ticket-status-badge ticket-status-badge--${ticketStatusTone(ticket.status)}`}
                        title={ticket.display_status_detail}
                      >
                        {ticket.display_status}
                      </span>
                    </div>
                    <p className="ticket-raised-item__detail">{ticket.display_status_detail}</p>
                    {ticket.similar_count > 1 ? (
                      <p className="ticket-raised-item__crowd">
                        {ticket.similar_count} students facing the same issue
                      </p>
                    ) : null}
                    {ticket.parent_ticket_id ? (
                      <p className="ticket-raised-item__crowd">Grouped with an existing open query</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-detail">No tickets raised in this conversation yet.</p>
            )}
          </div>
        </article>

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

        <article className="voice-history voice-history--sessions">
          <p className="section-kicker">Previous chats</p>
          <h2>Conversation history</h2>
          <div className="session-history">
            {earlierSessions.map((history) => (
              <details className="session-history__item" key={history.session_id}>
                <summary>
                  <span>{sessionTitle(history)}</span>
                  <time>{sessionDate(history.started_at)}</time>
                </summary>
                <div className="session-history__turns">
                  {history.turns.map((turn) => (
                    <p key={turn.id}>
                      <strong>{turn.speaker === "student" ? "You" : "Margdarshak"}:</strong>{" "}
                      {turn.content}
                    </p>
                  ))}
                </div>
              </details>
            ))}
            {!earlierSessions.length ? <p className="empty-detail">No previous conversations yet.</p> : null}
          </div>
        </article>
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
