import type { TicketWithCaseCard } from "../services/apiClient";

export type RaisedTicketsCardProps = {
  tickets: TicketWithCaseCard[];
  loading?: boolean;
};

function formatTicketDate(dateString: string): string {
  try {
    const date = new Date(dateString);
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

function ticketStatusTone(status: TicketWithCaseCard["status"]): "waiting" | "pending" | "resolved" {
  if (status === "escalated") return "pending";
  if (status === "resolved") return "resolved";
  return "waiting";
}

function ticketHeadline(ticket: TicketWithCaseCard): string {
  const summary = ticket.issue_summary.trim();
  if (summary) {
    return summary.length > 80 ? `${summary.slice(0, 77)}…` : summary;
  }
  const cardSummary = ticket.case_card?.issue_summary;
  if (typeof cardSummary === "string" && cardSummary.trim()) {
    return cardSummary.length > 80 ? `${cardSummary.slice(0, 77)}…` : cardSummary;
  }
  return "Placement support ticket";
}

export function RaisedTicketsCard({ tickets, loading = false }: RaisedTicketsCardProps) {
  // Only display tickets that have an issue summary or escalated/grouped status
  const visibleTickets = tickets.filter(
    (ticket) =>
      ticket.issue_summary.trim().length > 0 ||
      ticket.status === "escalated" ||
      ticket.parent_ticket_id !== null ||
      ticket.similar_count > 1
  );

  return (
    <article className="raised-tickets-card" aria-label="Raised Placement Tickets">
      <div className="raised-tickets-card__header">
        <div>
          <p className="section-kicker">Placement Issues</p>
          <h2 className="raised-tickets-card__title">Tickets Raised</h2>
        </div>
        <div className="raised-tickets-card__badge-wrapper">
          <span className="raised-tickets-count-badge">
            {visibleTickets.length} {visibleTickets.length === 1 ? "Active Ticket" : "Active Tickets"}
          </span>
        </div>
      </div>

      <p className="raised-tickets-card__description">
        Tickets formed when a placement issue or grievance is reported. Status and crowd counts update live.
      </p>

      {visibleTickets.length ? (
        <ul className="raised-tickets-list">
          {visibleTickets.map((ticket) => {
            const isResolved = ticket.status === "resolved";
            const isEscalated = ticket.status === "escalated";
            const hasMultipleStudents = ticket.similar_count > 1;

            // Visible highlight text explicitly requested by user:
            // "saying that if we are wating for a reply or if x number of students still wating for a reply"
            const highlightText = isResolved
              ? "Resolved · Response received"
              : hasMultipleStudents
                ? `${ticket.similar_count} students still waiting for a reply`
                : isEscalated
                  ? "Escalated to coordinator · Waiting for a reply"
                  : "Waiting for a reply";

            const highlightSubtext = isResolved
              ? "The placement team has addressed this inquiry."
              : hasMultipleStudents
                ? "This issue is affecting multiple candidates. Coordinator has been alerted."
                : isEscalated
                  ? "Assigned to the placement desk with your conversation context."
                  : "Your grievance is logged and queued for coordinator response.";

            return (
              <li key={ticket.id} className="ticket-card-item">
                <div className="ticket-card-item__top">
                  <div className="ticket-card-item__identity">
                    <span className="ticket-card-item__id">
                      #TK-{ticket.id.slice(0, 8).toUpperCase()}
                    </span>
                    <time className="ticket-card-item__time">
                      {formatTicketDate(ticket.created_at)}
                    </time>
                  </div>
                  <span
                    className={`ticket-status-badge ticket-status-badge--${ticketStatusTone(ticket.status)}`}
                  >
                    {ticket.display_status}
                  </span>
                </div>

                {/* THE PROMINENT VISIBLE HIGHLIGHT BANNER */}
                <div
                  className={`ticket-reply-highlight ${
                    isResolved
                      ? "ticket-reply-highlight--resolved"
                      : hasMultipleStudents
                        ? "ticket-reply-highlight--crowd"
                        : "ticket-reply-highlight--waiting"
                  }`}
                  role="status"
                >
                  <div className="ticket-reply-highlight__icon" aria-hidden="true">
                    {isResolved ? (
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                        <path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                      </svg>
                    ) : hasMultipleStudents ? (
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                        <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 3s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                        <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.2 14.2L11 13V7h1.5v5.2l4.5 2.7-.8 1.3z" />
                      </svg>
                    )}
                  </div>
                  <div className="ticket-reply-highlight__content">
                    <strong className="ticket-reply-highlight__lead">{highlightText}</strong>
                    <span className="ticket-reply-highlight__note">{highlightSubtext}</span>
                  </div>
                  {!isResolved ? (
                    <span className="ticket-reply-highlight__pulse" aria-hidden="true" />
                  ) : null}
                </div>

                <div className="ticket-card-item__body">
                  <strong className="ticket-card-item__headline">{ticketHeadline(ticket)}</strong>
                  {ticket.issue_summary && ticket.issue_summary !== ticketHeadline(ticket) ? (
                    <p className="ticket-card-item__summary">{ticket.issue_summary}</p>
                  ) : null}
                </div>

                <div className="ticket-card-item__footer">
                  {ticket.parent_ticket_id ? (
                    <span className="ticket-tag ticket-tag--grouped">
                      Grouped with open placement query
                    </span>
                  ) : null}
                  {ticket.escalated_to ? (
                    <span className="ticket-tag ticket-tag--desk">
                      Assigned: {ticket.escalated_to}
                    </span>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="raised-tickets-empty">
          <div className="raised-tickets-empty__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" strokeLinecap="round" strokeLinejoin="round" />
              <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
              <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" strokeLinejoin="round" />
              <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" strokeLinejoin="round" />
              <line x1="10" y1="9" x2="8" y2="9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h3>No placement tickets raised yet</h3>
          <p>
            When you raise a placement issue or grievance during your voice session, Margdarshak logs a ticket with the placement coordinator and tracks the reply status right here.
          </p>
        </div>
      )}
    </article>
  );
}
