const PIPELINE = [
  "Android UI",
  "Gemma 4 E2B via LiteRT-LM",
  "Workflow JSON",
  "Kotlin Safety Validator",
  "Room Database",
  "WorkManager Inactivity Worker",
  "Notification Verification",
  "User-approved Android Intent",
  "Emergency Log",
];

const STACK = [
  "Kotlin",
  "Jetpack Compose",
  "Gemma 4 E2B",
  "LiteRT-LM",
  "WorkManager",
  "Room",
  "DataStore",
  "Material 3",
];

export function Architecture() {
  return (
    <section className="py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            08 — Technical architecture
          </p>
          <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
            Technical architecture.
          </h2>
        </div>

        <div className="mt-14 grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <ol className="space-y-2">
            {PIPELINE.map((step, i) => (
              <li
                key={step}
                className="group flex items-center gap-4 rounded-2xl border hairline bg-card/50 px-5 py-4 transition-colors hover:bg-card"
              >
                <span className="font-mono text-[11px] text-muted-foreground">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-display text-base font-medium tracking-tight">{step}</span>
                {i < PIPELINE.length - 1 && (
                  <span aria-hidden className="ml-auto text-muted-foreground/40">↓</span>
                )}
              </li>
            ))}
          </ol>

          <div className="lg:sticky lg:top-28">
            <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Stack
            </h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {STACK.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center rounded-full border hairline bg-background px-3.5 py-1.5 font-mono text-[12px]"
                >
                  {s}
                </span>
              ))}
            </div>
            <p className="mt-8 text-[15px] leading-relaxed text-muted-foreground">
              Gemma creates the plan. Kotlin validates the JSON. WorkManager schedules the trigger.
              Android intents prepare the final user-approved action.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
