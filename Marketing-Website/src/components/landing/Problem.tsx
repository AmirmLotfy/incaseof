import { Home, Plane, Pill, HeartHandshake } from "lucide-react";

const CARDS = [
  { icon: Home, tag: "Living alone", quote: "What if nobody notices I disappeared?" },
  { icon: Plane, tag: "Travel", quote: "What if I never confirm I arrived?" },
  { icon: Pill, tag: "Medication", quote: "What if I miss a critical routine?" },
  { icon: HeartHandshake, tag: "Caregiving", quote: "What if someone needs help but cannot ask?" },
];

export function Problem() {
  return (
    <section id="problem" className="border-t hairline py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">01 — The problem</p>
            <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
              Most safety plans fail because they are never turned into action.
            </h2>
          </div>
          <p className="max-w-md text-lg text-muted-foreground text-pretty lg:justify-self-end">
            In Case of gives people a simple way to prepare for vulnerable
            moments before they happen — written in their own words, kept
            entirely on their device.
          </p>
        </div>
        <div className="mt-16 grid grid-cols-1 gap-px overflow-hidden rounded-3xl border hairline bg-border/50 md:grid-cols-2 lg:grid-cols-4">
          {CARDS.map(({ icon: Icon, tag, quote }, i) => (
            <article key={tag} className="group relative bg-background p-7 transition-colors hover:bg-card">
              <div className="flex items-center gap-3">
                <span className="grid size-9 place-items-center rounded-xl bg-foreground/[0.04] text-accent-violet">
                  <Icon className="size-4" />
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  0{i + 1}
                </span>
              </div>
              <h3 className="font-display mt-6 text-xl font-semibold tracking-tight">{tag}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">&ldquo;{quote}&rdquo;</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
