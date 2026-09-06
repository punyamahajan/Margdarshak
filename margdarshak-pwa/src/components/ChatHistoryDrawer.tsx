import { useEffect, useState, useId } from "react";
import type { VoiceHistorySession } from "../services/apiClient";
import { ConversationCard, extractConversationTitle } from "./ConversationCard";

export type ChatHistoryDrawerProps = {
  isOpen: boolean;
  onClose: () => void;
  sessions: VoiceHistorySession[];
  onStartNewChat?: () => void;
  loading?: boolean;
};

export function ChatHistoryDrawer({
  isOpen,
  onClose,
  sessions,
  onStartNewChat,
  loading = false,
}: ChatHistoryDrawerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const titleId = useId();

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Lock body scroll when open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const filteredSessions = sessions.filter((session) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const title = extractConversationTitle(session).toLowerCase();
    const matchesTurn = session.turns.some((t) => t.content.toLowerCase().includes(query));
    return title.includes(query) || matchesTurn;
  });

  return (
    <div
      className={`chat-history-drawer-wrapper ${isOpen ? "chat-history-drawer-wrapper--open" : ""}`}
      aria-hidden={!isOpen}
    >
      {/* Backdrop */}
      <div
        className="chat-history-drawer__backdrop"
        onClick={onClose}
        aria-label="Close chat history"
      />

      {/* Side Panel Panel */}
      <aside
        className="chat-history-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="chat-history-drawer__header">
          <div className="chat-history-drawer__title-group">
            <div className="chat-history-drawer__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14H6v-2h6v2zm4-4H6v-2h10v2zm0-4H6V7h10v2z" />
              </svg>
            </div>
            <div>
              <h2 id={titleId} className="chat-history-drawer__title">
                Chat History
              </h2>
              <span className="chat-history-drawer__subtitle">
                {sessions.length} {sessions.length === 1 ? "conversation" : "conversations"}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="chat-history-drawer__close"
            onClick={onClose}
            aria-label="Close side panel"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {onStartNewChat ? (
          <div className="chat-history-drawer__actions">
            <button
              type="button"
              className="chat-history-drawer__new-chat-btn"
              onClick={() => {
                onClose();
                onStartNewChat();
              }}
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>New voice conversation</span>
            </button>
          </div>
        ) : null}

        <div className="chat-history-drawer__search">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="search"
            placeholder="Search past conversations…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search conversation history"
          />
          {searchQuery ? (
            <button
              type="button"
              className="chat-history-drawer__search-clear"
              onClick={() => setSearchQuery("")}
              aria-label="Clear search"
            >
              ✕
            </button>
          ) : null}
        </div>

        <div className="chat-history-drawer__body">
          {loading ? (
            <div className="chat-history-drawer__loading">
              <span className="chat-history-drawer__spinner" aria-hidden="true" />
              <p>Loading your chat history…</p>
            </div>
          ) : filteredSessions.length ? (
            <div className="chat-history-drawer__list">
              {filteredSessions.map((session) => (
                <ConversationCard key={session.session_id} session={session} />
              ))}
            </div>
          ) : (
            <div className="chat-history-drawer__empty">
              <div className="chat-history-drawer__empty-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="1.6">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h3>{searchQuery ? "No matching chats" : "No conversations yet"}</h3>
              <p>
                {searchQuery
                  ? `No chats matched "${searchQuery}". Try a different search term.`
                  : "Your voice conversations with Margdarshak will be saved here."}
              </p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
