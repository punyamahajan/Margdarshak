export type SummaryCardVariant = "info" | "confirmation-needed" | "escalating";
export type SummaryCardContent = { label: string; value: string } | string;

type SummaryCardProps = {
  title: string;
  content: SummaryCardContent[];
  variant?: SummaryCardVariant;
  visible?: boolean;
};

const variantLabels: Record<SummaryCardVariant, string> = {
  info: "Call summary",
  "confirmation-needed": "Please confirm",
  escalating: "Human support"
};

export function SummaryCard({
  title,
  content,
  variant = "info",
  visible = true
}: SummaryCardProps) {
  return (
    <article
      className="summary-card"
      data-variant={variant}
      data-visible={visible}
      aria-hidden={!visible}
      aria-live="polite"
    >
      <p className="summary-card__eyebrow">{variantLabels[variant]}</p>
      <h2>{title}</h2>
      <ul className="summary-card__content">
        {content.slice(-5).map((item, index) => (
          <li key={typeof item === "string" ? `${item}-${index}` : `${item.label}-${index}`}>
            {typeof item === "string" ? item : (
              <><span>{item.label}</span><strong>{item.value}</strong></>
            )}
          </li>
        ))}
      </ul>
    </article>
  );
}
