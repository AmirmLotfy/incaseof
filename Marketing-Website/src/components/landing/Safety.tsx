const ITEMS = [
  {
    title: "No hidden monitoring",
    body: "The app does not spy on other people or run secret surveillance. Cases are visible and cancellable at any time.",
  },
  {
    title: "No automatic dangerous actions",
    body: "Gemma creates plans. Android code validates and asks for approval before any message is sent.",
  },
  {
    title: "No emergency-service replacement",
    body: "The app helps trusted contacts respond. It is not a medical, legal, or emergency dispatch system.",
  },
  {
    title: "Transparent logs",
    body: "Every trigger, notification, cancellation, and prepared action is recorded — and visible to you.",
  },
];

export function Safety() {
  return (
    <section className="bg-card/40 border-y hairline py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            07 — Consent first
          </p>
          <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
            Built with consent-first safety rules.
          </h2>
        </div>
        <div className="mt-14 grid gap-8 md:grid-cols-2">
          {ITEMS.map((it, i) => (
            <article key={it.title} className="rounded-3xl border hairline bg-background p-7">
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-[11px] tracking-[0.2em] text-accent-violet">
                  / 0{i + 1}
                </span>
                <h3 className="font-display text-xl font-semibold tracking-tight">{it.title}</h3>
              </div>
              <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">{it.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
