import { Download, ShieldAlert } from "lucide-react";

const META: Array<[string, string]> = [
  ["Version", "v1.0 Hackathon Build"],
  ["Platform", "Android 8.0+ (API 26+)"],
  ["Model", "Gemma 4 E2B · LiteRT-LM 0.11.0"],
  ["Package", "com.incaseof.app"],
  ["Updated", "May 2026"],
  ["SHA-256", "41638a14…bdb2f05a"],
];

export function Apk() {
  return (
    <section id="apk" className="relative overflow-hidden py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative overflow-hidden rounded-[32px] border hairline bg-card/70 p-8 shadow-elev backdrop-blur md:p-14">
          <div className="absolute -right-32 -top-32 size-[28rem] rounded-full bg-accent-cyan/30 blur-3xl" />
          <div className="absolute -bottom-32 -left-32 size-[28rem] rounded-full bg-accent-violet/25 blur-3xl" />

          <div className="relative grid gap-12 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent-violet">
                05 — Try the prototype
              </p>
              <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-6xl">
                Try the Android prototype.
              </h2>
              <p className="mt-5 max-w-xl text-lg text-muted-foreground text-pretty">
                Install the hackathon APK and test the safety workflow simulation on your
                Android device. Create a case, review the Gemma-generated plan, trigger a
                missed check-in, and prepare a trusted-contact alert.
              </p>

              <div className="mt-9 flex flex-col gap-3 sm:flex-row">
                <a
                  href="/downloads/in-case-of-v1.apk"
                  download
                  className="group inline-flex items-center justify-center gap-2 rounded-full bg-foreground px-7 py-4 text-[15px] font-medium text-background shadow-[0_20px_60px_-15px_oklch(0.16_0.06_280/45%)] transition-transform hover:-translate-y-0.5 active:scale-[0.98]"
                >
                  <Download className="size-4" />
                  Download Android APK
                </a>
                <a
                  href="#demo"
                  className="inline-flex items-center justify-center gap-2 rounded-full border hairline bg-background px-7 py-4 text-[15px] font-medium transition-colors hover:bg-card"
                >
                  Watch demo first
                </a>
              </div>

              <div className="mt-6 flex items-start gap-2 rounded-2xl border hairline bg-background/60 p-4 text-sm text-muted-foreground">
                <ShieldAlert className="mt-0.5 size-4 shrink-0 text-accent-coral" />
                <p>
                  Android may ask you to allow installation from your browser. This APK is a
                  hackathon prototype. <span className="text-foreground">It is not a replacement for emergency services.</span>
                </p>
              </div>
            </div>

            <div className="rounded-[22px] border border-foreground/10 bg-foreground p-6 text-background md:p-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-background/50">
                Build details
              </p>
              <dl className="mt-5 divide-y divide-white/10">
                {META.map(([k, v]) => (
                  <div key={k} className="flex items-baseline justify-between gap-4 py-3 text-sm">
                    <dt className="text-background/50">{k}</dt>
                    <dd className="max-w-[60%] truncate text-right font-mono text-[13px]">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
