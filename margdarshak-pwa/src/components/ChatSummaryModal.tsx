import { useEffect, useState, useId } from "react";
import {
  apiClient,
  type VoiceHistorySession,
  type VoiceSessionSummary,
  type VoiceSessionSummaryLink,
} from "../services/apiClient";
import {
  extractLinksFromSession,
  generateClientSessionSummary,
  type ExtractedLink,
} from "../utils/sessionSummary";

export type ChatSummaryModalProps = {
  isOpen: boolean;
  session: VoiceHistorySession | null;
  onClose: () => void;
};

function formatSessionDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  } catch {
    return dateString;
  }
}

export function ChatSummaryModal({ isOpen, session, onClose }: ChatSummaryModalProps) {
  const [activeTab, setActiveTab] = useState<"summary" | "links" | "transcript">("summary");
  const [backendData, setBackendData] = useState<VoiceSessionSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedLinkUrl, setCopiedLinkUrl] = useState<string | null>(null);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [copiedAllLinks, setCopiedAllLinks] = useState(false);

  const titleId = useId();

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Fetch backend summary when session changes
  useEffect(() => {
    if (!isOpen || !session) {
      setBackendData(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setActiveTab("summary");

    apiClient
      .getVoiceSessionSummary(session.session_id)
      .then((data) => {
        if (isMounted) {
          setBackendData(data);
        }
      })
      .catch(() => {
        // graceful fallback to client synthesized data
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, session]);

  if (!isOpen || !session) return null;

  // Compute fallback / instant client synthesized data
  const clientSummary = generateClientSessionSummary(session);
  const clientLinks = extractLinksFromSession(session);

  // Merge backend links with client extracted links
  const mergedLinks: ExtractedLink[] = [...clientLinks];
  if (backendData?.links) {
    for (const bLink of backendData.links) {
      if (!mergedLinks.some((l) => l.url.toLowerCase() === bLink.url.toLowerCase())) {
        try {
          const parsed = new URL(bLink.url);
          mergedLinks.push({
            url: bLink.url,
            title: bLink.title || parsed.hostname,
            domain: parsed.hostname.replace(/^www\./, ""),
            source: "recommendation",
            category: bLink.category || "AI Resource",
            snippet: bLink.snippet,
          });
        } catch {
          // ignore malformed
        }
      }
    }
  }

  // Display details
  const displayTopic = backendData?.topic || clientSummary.topic;
  const displayStatus = backendData?.summary?.status || clientSummary.statusBadge;
  const formattedDate = formatSessionDate(session.started_at);
  const turns = backendData?.turns || session.turns;

  const handleCopyLink = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedLinkUrl(url);
      window.setTimeout(() => setCopiedLinkUrl(null), 2000);
    } catch {
      // ignore
    }
  };

  const handleCopyAllLinks = async () => {
    if (!mergedLinks.length) return;
    const text = mergedLinks.map((l) => `${l.title}: ${l.url}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAllLinks(true);
      window.setTimeout(() => setCopiedAllLinks(false), 2000);
    } catch {
      // ignore
    }
  };

  const handleCopySummary = async () => {
    const lines = [
      `Chat Summary: ${displayTopic}`,
      `Date: ${formattedDate}`,
      `Status: ${displayStatus}`,
      ``,
      `Student Query:`,
      backendData?.summary?.student_query || clientSummary.studentQuery,
      ``,
      `Margdarshak Resolution:`,
      backendData?.summary?.ai_guidance || clientSummary.aiGuidance,
    ];
    if (mergedLinks.length > 0) {
      lines.push(``, `Resources & Links:`);
      mergedLinks.forEach((l) => lines.push(`- ${l.title}: ${l.url}`));
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopiedSummary(true);
      window.setTimeout(() => setCopiedSummary(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="chat-summary-modal-backdrop" onClick={onClose}>
      <div
        className="chat-summary-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="chat-summary-modal__header">
          <div className="chat-summary-modal__title-group">
            <div className="chat-summary-modal__pill-row">
              <span className="chat-summary-modal__date">{formattedDate}</span>
              <span className={`chat-summary-modal__status-tag ${displayStatus.includes("Escalated") ? "chat-summary-modal__status-tag--escalated" : ""}`}>
                {displayStatus}
              </span>
              {loading && <span className="chat-summary-modal__syncing">Updating…</span>}
            </div>
            <h2 id={titleId} className="chat-summary-modal__title">
              {displayTopic}
            </h2>
          </div>

          <button
            type="button"
            className="chat-summary-modal__close-btn"
            onClick={onClose}
            aria-label="Close summary modal"
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="chat-summary-modal__tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "summary"}
            className={`chat-summary-modal__tab ${activeTab === "summary" ? "chat-summary-modal__tab--active" : ""}`}
            onClick={() => setActiveTab("summary")}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
              <path d="M12 2l2.4 7.2h7.6l-6.1 4.5 2.3 7.3-6.2-4.5-6.2 4.5 2.3-7.3-6.1-4.5h7.6z" />
            </svg>
            <span>Summary</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "links"}
            className={`chat-summary-modal__tab ${activeTab === "links" ? "chat-summary-modal__tab--active" : ""}`}
            onClick={() => setActiveTab("links")}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <span>AI Links & Resources</span>
            {mergedLinks.length > 0 && (
              <span className="chat-summary-modal__count-pill">{mergedLinks.length}</span>
            )}
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "transcript"}
            className={`chat-summary-modal__tab ${activeTab === "transcript" ? "chat-summary-modal__tab--active" : ""}`}
            onClick={() => setActiveTab("transcript")}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
            </svg>
            <span>Full Transcript</span>
            <span className="chat-summary-modal__turn-pill">{turns.length} turns</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="chat-summary-modal__body">
          {activeTab === "summary" && (
            <div className="chat-summary-tab-content">
              {/* Recommendation Callout if available */}
              {backendData?.recommendation && (
                <div className="chat-summary-callout">
                  <div className="chat-summary-callout__badge">
                    <span>Recommended Learning Resource</span>
                  </div>
                  <h4 className="chat-summary-callout__title">{backendData.recommendation.title}</h4>
                  <p className="chat-summary-callout__reasoning">
                    {backendData.recommendation.reasoning}
                  </p>
                  <div className="chat-summary-callout__meta">
                    <span className="chat-summary-meta-tag">{backendData.recommendation.format}</span>
                    <span className="chat-summary-meta-tag">{backendData.recommendation.pacing} pace</span>
                    <span className="chat-summary-meta-tag">{backendData.recommendation.price_tier}</span>
                    <a
                      href={backendData.recommendation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="chat-summary-callout__open-link"
                    >
                      Open Resource ↗
                    </a>
                  </div>
                </div>
              )}

              {/* Student Query Section */}
              <div className="chat-summary-section">
                <div className="chat-summary-section__header">
                  <span className="chat-summary-section__avatar chat-summary-section__avatar--student">You</span>
                  <h3>What was asked / discussed</h3>
                </div>
                <div className="chat-summary-section__quote">
                  <p>{backendData?.summary?.student_query || clientSummary.studentQuery}</p>
                </div>
              </div>

              {/* Margdarshak Resolution Section */}
              <div className="chat-summary-section">
                <div className="chat-summary-section__header">
                  <span className="chat-summary-section__avatar chat-summary-section__avatar--agent">M</span>
                  <h3>Margdarshak Resolution & Guidance</h3>
                </div>
                <div className="chat-summary-section__card">
                  <p>{backendData?.summary?.ai_guidance || clientSummary.aiGuidance}</p>
                </div>
              </div>

              {/* Key Takeaways */}
              {clientSummary.keyPoints.length > 0 && (
                <div className="chat-summary-section">
                  <div className="chat-summary-section__header">
                    <span className="chat-summary-section__bullet-icon">✓</span>
                    <h3>Key Highlights & Takeaways</h3>
                  </div>
                  <ul className="chat-summary-bullets">
                    {clientSummary.keyPoints.map((point, i) => (
                      <li key={i}>{point}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Links preview row if any links exist */}
              {mergedLinks.length > 0 && (
                <div className="chat-summary-quick-links">
                  <div className="chat-summary-quick-links__header">
                    <h4>Resources shared in this chat ({mergedLinks.length})</h4>
                    <button
                      type="button"
                      className="chat-summary-view-all-btn"
                      onClick={() => setActiveTab("links")}
                    >
                      View all links →
                    </button>
                  </div>
                  <div className="chat-summary-quick-links__chips">
                    {mergedLinks.slice(0, 3).map((l, i) => (
                      <a
                        key={i}
                        href={l.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="chat-summary-link-chip"
                      >
                        <span className="chat-summary-link-chip__domain">{l.domain}</span>
                        <span className="chat-summary-link-chip__title">{l.title}</span>
                        <span aria-hidden="true">↗</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "links" && (
            <div className="chat-links-tab-content">
              {mergedLinks.length > 0 ? (
                <>
                  <div className="chat-links-toolbar">
                    <p className="chat-links-toolbar__info">
                      <strong>{mergedLinks.length}</strong> {mergedLinks.length === 1 ? "resource was" : "resources were"} provided by the AI during this session.
                    </p>
                    <button
                      type="button"
                      className="chat-links-copy-all-btn"
                      onClick={handleCopyAllLinks}
                    >
                      {copiedAllLinks ? "✓ Copied All Links" : "Copy All Links"}
                    </button>
                  </div>

                  <div className="chat-links-grid">
                    {mergedLinks.map((link, idx) => (
                      <div key={idx} className="chat-link-card">
                        <div className="chat-link-card__top">
                          <div className="chat-link-card__meta">
                            <span className="chat-link-card__domain-badge">{link.domain}</span>
                            {link.category && (
                              <span className="chat-link-card__category">{link.category}</span>
                            )}
                          </div>
                          <button
                            type="button"
                            className="chat-link-card__copy-btn"
                            onClick={() => handleCopyLink(link.url)}
                            title="Copy link to clipboard"
                          >
                            {copiedLinkUrl === link.url ? "✓ Copied" : "Copy"}
                          </button>
                        </div>

                        <h4 className="chat-link-card__title">
                          <a href={link.url} target="_blank" rel="noopener noreferrer">
                            {link.title}
                            <span className="chat-link-card__external-icon" aria-hidden="true"> ↗</span>
                          </a>
                        </h4>

                        <p className="chat-link-card__url">{link.url}</p>

                        {link.snippet && (
                          <p className="chat-link-card__snippet">
                            <span className="chat-link-card__snippet-label">Mentioned: </span>
                            "{link.snippet}"
                          </p>
                        )}

                        <div className="chat-link-card__footer">
                          <a
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="chat-link-card__visit-btn"
                          >
                            Open Link ↗
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="chat-links-empty">
                  <div className="chat-links-empty__icon">🔗</div>
                  <h3>No external links were shared</h3>
                  <p>
                    During this session, Margdarshak answered via voice without providing explicit external links.
                  </p>
                  <p className="chat-links-empty__tip">
                    <strong>Tip:</strong> You can ask Margdarshak: <em>"Can you share the link for the Striver SDE sheet or the college drive portal?"</em> and it will automatically generate and attach the resource!
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === "transcript" && (
            <div className="chat-transcript-tab-content">
              {turns.length > 0 ? (
                <div className="chat-transcript-turns">
                  {turns.map((turn) => {
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
                            {isStudent ? "You" : "Margdarshak AI"}
                          </div>
                          <p className="conversation-bubble__text">{turn.content}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="chat-transcript-empty">No spoken turns recorded in this session.</p>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="chat-summary-modal__footer">
          <div className="chat-summary-modal__footer-actions">
            <button
              type="button"
              className="chat-summary-modal__btn chat-summary-modal__btn--secondary"
              onClick={handleCopySummary}
            >
              {copiedSummary ? "✓ Copied Summary" : "Copy Summary"}
            </button>
            {mergedLinks.length > 0 && (
              <button
                type="button"
                className="chat-summary-modal__btn chat-summary-modal__btn--secondary"
                onClick={handleCopyAllLinks}
              >
                {copiedAllLinks ? "✓ Copied Links" : "Copy All Links"}
              </button>
            )}
          </div>

          <button
            type="button"
            className="chat-summary-modal__btn chat-summary-modal__btn--primary"
            onClick={onClose}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
