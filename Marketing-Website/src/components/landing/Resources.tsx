import { Play, Github, Download, FileText, Check } from "lucide-react";

const LINKS = [
  { icon: Play, label: "Watch Demo Video", href: "#", primary: false },
  { icon: Github, label: "View Source Code", href: "https://github.com/AmirmLotfy/incaseof", primary: false },
  { icon: Download, label: "Download APK", href: "/downloads/in-case-of-v1.apk", primary: true, download: true },
  { icon: FileText, label: "Read Writeup", href: "https://github.com/AmirmLotfy/incaseof/blob/main/KAGGLE_WRITEUP.md", primary: false },
];

const CHECKLIST = [
  "Public demo video",
  "Public code repository",
  "Functional prototype APK",
  "Technical architecture",
  "Gemma 4 usage explanation",
];

export function Resources() {
  return (
    <section id="resources" className="border-t hairline py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              09 — Hackathon resources
            </p>
            <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
              Everything a judge needs, in one place.
            </h2>
            <div className="mt-10 grid gap-3 sm:grid-cols-2">
              {LINKS.map(({ icon: Icon, label, href, primary, download }) => (
                <a
                  key={label}
                  href={href}
                  download={download}
                  className={`group inline-flex items-center justify-between gap-3 rounded-2xl border px-5 py-4 text-[15px] font-medium transition-all ${
                    primary
                      ? "border-foreground bg-foreground text-background hover:-translate-y-0.5"
                      : "hairline bg-card/60 hover:bg-card"
                  }`}
                >
                  <span className="inline-flex items-center gap-3">
                    <Icon className="size-4" /> {label}
                  </span>
                  <span className="opacity-50 transition-transform group-hover:translate-x-0.5">→</span>
                </a>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border hairline bg-card/60 p-7">
            <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Submission checklist
            </h3>
            <ul className="mt-5 space-y-3">
              {CHECKLIST.map((c) => (
                <li key={c} className="flex items-center gap-3 text-[15px]">
                  <span className="grid size-5 place-items-center rounded-full bg-accent-violet/15 text-accent-violet">
                    <Check className="size-3" />
                  </span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
