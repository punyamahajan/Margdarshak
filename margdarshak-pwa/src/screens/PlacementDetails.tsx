import type { Placement } from "../data/studentData";

type PlacementDetailsProps = { placement: Placement; onBack: () => void; onAsk: () => void };

export function PlacementDetails({ placement, onBack, onAsk }: PlacementDetailsProps) {
  return (
    <main className="placement-details">
      <header className="detail-nav">
        <button className="text-button" type="button" onClick={onBack}>← Back to placements</button>
        <span className="home-brand"><span className="home-brand__mark" aria-hidden="true">M</span>Margdarshak</span>
      </header>

      <section className="detail-hero">
        <div>
          <p className="section-kicker">{placement.driveId}</p>
          <h1>{placement.company}</h1>
          <p>{placement.role}</p>
        </div>
        <span className="detail-status">{placement.status}</span>
      </section>

      <div className="detail-grid">
        <section className="detail-card detail-card--primary">
          <p className="section-kicker">Your current stage</p>
          <h2>{placement.currentRound}</h2>
          <dl className="detail-facts">
            <div><dt>Deadline</dt><dd><time dateTime={placement.deadline}>{placement.deadlineLabel}</time></dd></div>
            <div><dt>CTC</dt><dd>{placement.ctc}</dd></div>
            <div><dt>Drive ID</dt><dd>{placement.driveId}</dd></div>
          </dl>
          <a className="detail-apply" href={placement.applicationUrl} target="_blank" rel="noreferrer">Open placement portal ↗</a>
        </section>

        <section className="detail-card">
          <p className="section-kicker">Eligibility</p>
          <h2>You meet the listed criteria</h2>
          <ul className="check-list">{placement.eligibility.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>

        <section className="detail-card">
          <p className="section-kicker">Instructions</p>
          <h2>Before you continue</h2>
          <ol className="instruction-list">{placement.instructions.map((item) => <li key={item}>{item}</li>)}</ol>
        </section>

        <aside className="source-card">
          <span className="source-card__verified">✓ Verified source</span>
          <strong>{placement.source.title}</strong>
          <span>Version {placement.source.version}</span>
          <small>{placement.source.reference}</small>
        </aside>
      </div>

      <section className="detail-help">
        <div><p className="section-kicker">Need help?</p><h2>Ask about this placement drive</h2></div>
        <button type="button" onClick={onAsk}>Start a voice conversation →</button>
      </section>
    </main>
  );
}
