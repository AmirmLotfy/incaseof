import { Languages, ShieldAlert, MessageSquareText, FlaskConical, Lock } from "lucide-react";

const CARDS = [
  { icon: Languages, title: "Natural language → workflow JSON", body: "Compiles plain sentences into a strict, typed plan." },
  { icon: ShieldAlert, title: "Risk & permission explanation", body: "Surfaces what each action will do — in human terms." },
  { icon: MessageSquareText, title: "Safe message generation", body: "Calm, factual templates for trusted-contact alerts." },
  { icon: FlaskConical, title: "Simulation-ready plan", body: "Run the workflow as a dry-run before enabling it." },
  { icon: Lock, title: "Local-first privacy story", body: "Inference runs on-device with LiteRT-LM. No cloud round-trip." },
];

const JSON_LINES: Array<[string, string, "key" | "str" | "num" | "bool"]> = [
  ["", "{", "key"],
  ["  ", '"trigger"', "key"],
  ["  ", '"missed_checkin"', "str"],
  ["  ", '"durationHours"', "key"],
  ["  ", "24", "num"],
  ["  ", '"verification"', "key"],
  ["  ", '"ask_if_safe"', "str"],
  ["  ", '"waitMinutes"', "key"],
  ["  ", "15", "num"],
  ["  ", '"action"', "key"],
  ["  ", '"prepare_sms"', "str"],
  ["  ", '"requiresApproval"', "key"],
  ["  ", "true", "bool"],
  ["", "}", "key"],
];

export function Gemma() {
  return (
    <section id="gemma" className="border-t hairline py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              04 — Why Gemma 4
            </p>
            <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-5xl">
              Why Gemma 4 matters here.
            </h2>
            <p className="mt-6 max-w-lg text-lg text-muted-foreground text-pretty">
              In Case of uses Gemma 4 as a local safety workflow planner. It converts messy
              natural language into structured JSON, detects risky requests, explains
              permissions, and generates calm emergency messages.
            </p>
            <ul className="mt-10 grid gap-3 sm:grid-cols-2">
              {CARDS.map(({ icon: Icon, title, body }) => (
                <li key={title} className="rounded-2xl border hairline bg-card/60 p-5 backdrop-blur">
                  <Icon className="size-4 text-accent-violet" />
                  <h3 className="font-display mt-3 text-[15px] font-semibold tracking-tight">{title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{body}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="relative">
            <div className="absolute -inset-10 -z-10 rounded-[2rem] bg-gradient-to-br from-accent-cyan/20 via-transparent to-accent-violet/20 blur-3xl" />
            <figure className="overflow-hidden rounded-[20px] border border-foreground/10 bg-foreground text-background shadow-elev">
              <header className="flex items-center justify-between border-b border-white/10 px-5 py-3">
                <div className="flex gap-1.5">
                  <span className="size-2.5 rounded-full bg-white/20" />
                  <span className="size-2.5 rounded-full bg-white/20" />
                  <span className="size-2.5 rounded-full bg-white/20" />
                </div>
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] opacity-50">
                  workflow.json · gemma-4 e2b
                </span>
              </header>
              <pre className="overflow-x-auto p-6 font-mono text-[13px] leading-relaxed">
                {JSON_LINES.map(([indent, tok, kind], i) => (
                  <div key={i}>
                    <span>{indent}</span>
                    <Token kind={kind}>{tok}</Token>
                    {i > 0 && i < JSON_LINES.length - 1 && i % 2 === 0 ? "," : ""}
                    {i > 0 && i < JSON_LINES.length - 1 && i % 2 === 1 ? ":" : ""}
                  </div>
                ))}
              </pre>
            </figure>
          </div>
        </div>
      </div>
    </section>
  );
}

function Token({ kind, children }: { kind: "key" | "str" | "num" | "bool"; children: React.ReactNode }) {
  const cls = {
    key: "text-accent-cyan",
    str: "text-accent-coral",
    num: "text-accent-violet",
    bool: "text-accent-violet",
  }[kind];
  return <span className={cls}>{children}</span>;
}
