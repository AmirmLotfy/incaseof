import screensWebp from "@/assets/screens-row.webp";
import screensImg from "@/assets/screens-row.png";

const CAPTIONS = [
  { tag: "Create Case", body: "Two sentences. That's the whole input." },
  { tag: "Safety Review", body: "See exactly what will happen before anything is enabled." },
  { tag: "Active Case", body: "A calm dashboard for the next check-in." },
  { tag: "Missed Check-in", body: "A clear, single-tap question: are you okay?" },
  { tag: "Emergency Log", body: "Every trigger, prompt, and prepared action — recorded." },
];

export function Screens() {
  return (
    <section className="border-t hairline py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              06 — App screens
            </p>
            <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
              Designed for high-stress moments.
            </h2>
          </div>
          <p className="max-w-md text-lg text-muted-foreground text-pretty lg:justify-self-end">
            Big targets. Clear language. Nothing that adds friction in the moment
            it matters most.
          </p>
        </div>

        <div className="relative mt-14 overflow-hidden rounded-[28px] border hairline bg-gradient-to-b from-card/60 to-background p-2 md:p-4">
          {/* Explicit aspect-ratio prevents CLS on lazy-load */}
          <div style={{ aspectRatio: '1536/1024' }}>
            <picture>
              <source srcSet={screensWebp} type="image/webp" />
              <img
                src={screensImg}
                alt="Five In Case of app screens: Create Case, Safety Review, Active Case, Missed Check-in, Emergency Log"
                width={1536}
                height={1024}
                loading="lazy"
                decoding="async"
                className="w-full h-full object-cover"
              />
            </picture>
          </div>
        </div>

        <ul className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border hairline bg-border/50 sm:grid-cols-2 lg:grid-cols-5">
          {CAPTIONS.map((c, i) => (
            <li key={c.tag} className="bg-background p-5">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                0{i + 1}
              </div>
              <h3 className="font-display mt-2 text-[15px] font-semibold tracking-tight">{c.tag}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{c.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
