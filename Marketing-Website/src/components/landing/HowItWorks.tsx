const STEPS = [
  "User describes a case",
  "Gemma 4 converts it to JSON",
  "Kotlin validates safety rules",
  "WorkManager watches for missed check-ins",
  'Notification asks "Are you okay?"',
  "Approved action is prepared",
  "Every step is logged",
];

export function HowItWorks() {
  return (
    <section id="how" className="border-t hairline py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
          <div className="lg:sticky lg:top-28">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              03 — How it works
            </p>
            <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
              Gemma plans. Android validates. You stay in control.
            </h2>
            <p className="mt-6 max-w-md text-lg text-muted-foreground text-pretty">
              The model never directly executes dangerous actions. It creates a plan.
              The app validates, schedules, confirms, and logs.
            </p>
          </div>

          <ol className="relative">
            <span aria-hidden className="absolute left-[15px] top-2 bottom-2 w-px bg-border" />
            {STEPS.map((step, i) => (
              <li key={step} className="relative flex gap-5 pb-8 last:pb-0">
                <span className="relative z-10 mt-0.5 grid size-8 shrink-0 place-items-center rounded-full border hairline bg-background font-mono text-[11px] font-medium">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div className="pt-1">
                  <p className="font-display text-lg font-medium tracking-tight">{step}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
