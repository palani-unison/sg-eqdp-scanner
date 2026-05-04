import { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: ReactNode;
  dek?: ReactNode;
  meta?: ReactNode;
  large?: boolean;
};

/**
 * Section / page header in the editorial style:
 *
 *   READ · METHODOLOGY                              ← eyebrow
 *   ──                                              ← rule
 *   How we reverse-engineer who got bought          ← serif display title
 *   The single biggest mistake is to measure...     ← italic dek
 */
export function EditorialHeader({ eyebrow, title, dek, meta, large }: Props) {
  return (
    <header className="mb-10">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      {eyebrow && <div className="rule mt-2" />}
      <h1
        className={
          large
            ? "display-large text-5xl sm:text-6xl text-ink"
            : "display text-3xl sm:text-4xl text-ink"
        }
      >
        {title}
      </h1>
      {dek && <p className="dek mt-4 max-w-prose">{dek}</p>}
      {meta && (
        <p className="mt-4 text-xs text-ink-faint tracking-wide">{meta}</p>
      )}
    </header>
  );
}
