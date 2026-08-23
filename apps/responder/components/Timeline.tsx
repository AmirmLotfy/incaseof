import { clockTime, eventLabel, type TimelineEntry } from "@/lib/incident";

/**
 * What has already been tried.
 *
 * A literal list of times and events. This is the part that turns "somebody needs you" into
 * a decision somebody can actually make — knowing three attempts already failed is what
 * tells a responder this is worth getting up for.
 *
 * An ordered list, so a screen reader reads it as a sequence and announces its length.
 */
export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  if (entries.length === 0) {
    return <p style={{ color: "var(--ico-graphite)" }}>Nothing has been tried yet.</p>;
  }

  return (
    <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {entries.map((entry, index) => (
        <li
          key={`${entry.at}-${index}`}
          // Asserted on in test/a11y.test.ts. Visual order and DOM order can disagree, and
          // a timeline that reads backwards to a screen reader tells the story in reverse.
          data-timeline-at={entry.at}
          style={{
            display: "grid",
            gridTemplateColumns: "5.5rem 1fr",
            gap: "0.75rem",
            padding: "0.5rem 0",
            alignItems: "baseline",
          }}
        >
          <span className="tabular" style={{ color: "var(--ico-graphite)" }}>
            {clockTime(entry.at)}
          </span>
          <span>{eventLabel(entry.event)}</span>
        </li>
      ))}
    </ol>
  );
}
