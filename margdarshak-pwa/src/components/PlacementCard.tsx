import type { Placement } from "../data/studentData";

type PlacementCardProps = {
  placement: Placement;
  onOpen: (id: string) => void;
};

export function PlacementCard({ placement, onOpen }: PlacementCardProps) {
  return (
    <article className="placement-card">
      <div className="placement-card__topline">
        <span className="placement-card__status">{placement.status}</span>
        <span>{placement.driveId}</span>
      </div>
      <h3>{placement.company}</h3>
      <p className="placement-card__role">{placement.role}</p>
      <p className="placement-card__round">{placement.currentRound}</p>
      <dl>
        <div><dt>Deadline</dt><dd>{placement.deadlineLabel}</dd></div>
        <div><dt>CTC</dt><dd>{placement.ctc}</dd></div>
      </dl>
      <button type="button" onClick={() => onOpen(placement.id)}>
        View verified details <span aria-hidden="true">→</span>
      </button>
    </article>
  );
}
