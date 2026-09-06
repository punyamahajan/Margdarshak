import { useState } from "react";
import type { VoiceHistorySession } from "../services/apiClient";

export type ConversationCardProps = {
  session: VoiceHistorySession;
  defaultExpanded?: boolean;
  onOpenSummary?: (session: VoiceHistorySession) => void;
};

function formatSessionDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const isToday =
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear();

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday =
      date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear();

    const timeStr = new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
    }).format(date);

    if (isToday) return `Today · ${timeStr}`;
    if (isYesterday) return `Yesterday · ${timeStr}`;

    return new Intl.DateTimeFormat(undefined, {
      day: "numeric",
      month: "short",
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  } catch {
    return dateString;
  }
}

export function extractConversationTitle(session: VoiceHistorySession): string {
  const firstStudentTurn = session.turns.find((t) => t.speaker === "student" && t.content.trim());
  if (firstStudentTurn) {
    const clean = firstStudentTurn.content.trim();
    const capitalized = clean.charAt(0).toUpperCase() + clean.slice(1);
    return capitalized.length > 56 ? `${capitalized.slice(0, 53)}…` : capitalized;
  }
  const firstAgentTurn = session.turns.find((t) => t.content.trim());
  if (firstAgentTurn) {
    const clean = firstAgentTurn.content.trim();
    const capitalized = clean.charAt(0).toUpperCase() + clean.slice(1);
    return capitalized.length > 56 ? `${capitalized.slice(0, 53)}…` : capitalized;
  }
  return "Voice guidance session";
}

export function ConversationCard({
  session,
  defaultExpanded = false,
  onOpenSummary,
}: ConversationCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const title = extractConversationTitle(session);
  const formattedDate = formatSessionDate(session.started_at);
  const turnCount = session.turns.length;

  const previewSnippet = session.turns.find((t) => t.content.trim())?.content.trim() ?? "";

  const handleCardClick = () => {
    if (onOpenSummary) {
      onOpenSummary(session);
    } else {
      setExpanded(!expanded);
    }
  };

  const copyTranscript = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!session.turns.length) return;
    const transcriptText = session.turns
      .map((turn) => `${turn.speaker === "student" ? "You" : "Margdarshak"}: ${turn.content}`)
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(transcriptText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard write failed silently
    }
  };

  return (
    <article
      className={`conversation-card ${expanded ? "conversation-card--expanded" : ""}`}
      aria-expanded={expanded}
    >
      <div
        role="button"
        tabIndex={0}
        className="conversation-card__trigger"
        onClick={handleCardClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleCardClick();
          }
        }}
        aria-label={`${title}, ${formattedDate}. Click to view chat summary and resources.`}
      >
        <div className="conversation-card__header">
          <div className="conversation-card__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H7.414L3.707 21.707A1 1 0 0 1 2 21V6a2 2 0 0 1 2-2zm0 2v12.586l2.293-2.293A1 1 0 0 1 7 16h13V6H4z" />
            </svg>
          </div>
          <div className="conversation-card__heading">
            <h3 className="conversation-card__title">{title}</h3>
            <div className="conversation-card__meta">
              <span className="conversation-card__date">{formattedDate}</span>
              <span className="conversation-card__turn-badge">
                {turnCount === 0
                  ? "No speech"
                  : `${turnCount} ${turnCount === 1 ? "turn" : "turns"}`}
              </span>
              <span
                className="conversation-card__summary-pill"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenSummary ? onOpenSummary(session) : setExpanded(!expanded);
                }}
              >
                Summary & Links ↗
              </span>
            </div>
          </div>
          <div
            className={`conversation-card__chevron ${expanded ? "conversation-card__chevron--rotated" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            title={expanded ? "Collapse inline preview" : "Expand inline preview"}
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>

        {!expanded && previewSnippet ? (
          <p className="conversation-card__snippet">
            "{previewSnippet.length > 90 ? `${previewSnippet.slice(0, 87)}…` : previewSnippet}"
          </p>
        ) : null}
      </div>

      {expanded ? (
        <div className="conversation-card__content">
          <div className="conversation-card__turns">
            {session.turns.length ? (
              session.turns.map((turn) => {
                const isStudent = turn.speaker === "student";
                return (
                  <div
                    key={turn.id}
                    className={`conversation-bubble ${
                      isStudent ? "conversation-bubble--student" : "conversation-bubble--agent"
                    }`}
                  >
                    <div className="conversation-bubble__avatar" aria-hidden="true">
                      {isStudent ? "You" : "M"}
                    </div>
                    <div className="conversation-bubble__body">
                      <div className="conversation-bubble__author">
                        {isStudent ? "You" : "Margdarshak"}
                      </div>
                      <p className="conversation-bubble__text">{turn.content}</p>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="conversation-card__empty-turns">
                Call was connected, but no speech was transcribed.
              </p>
            )}
          </div>
          {session.turns.length ? (
            <div className="conversation-card__actions">
              <button
                type="button"
                className="conversation-card__copy-btn"
                onClick={copyTranscript}
              >
                {copied ? "✓ Copied transcript" : "Copy transcript"}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
