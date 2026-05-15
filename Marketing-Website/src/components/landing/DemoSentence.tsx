import { motion } from "motion/react";
import { Sparkles, ArrowRight } from "lucide-react";

const STEPS = [
  { kind: "Trigger", body: "No check-in for 24 hours", color: "cyan" },
  { kind: "Verification", body: 'Send "Are you okay?" notification', color: "violet" },
  { kind: "Wait", body: "15 minutes", color: "violet" },
  { kind: "Action", body: "Prepare SMS to trusted contact", color: "coral" },
  { kind: "Safety", body: "Require user approval · log every step", color: "cyan" },
] as const;

const COLOR: Record<string, string> = {
  cyan: "text-accent-cyan",
  violet: "text-accent-violet",
  coral: "text-accent-coral",
};

export function DemoSentence() {
  return (
    <section id="demo" className="relative overflow-hidden bg-foreground py-28 text-background md:py-36">
      <div className="absolute inset-0 -z-0 opacity-30 [background:radial-gradient(ellipse_50%_40%_at_30%_20%,oklch(0.88_0.14_215/30%),transparent_70%),radial-gradient(ellipse_50%_40%_at_70%_80%,oklch(0.62_0.22_295/30%),transparent_70%)]" />
      <div className="relative mx-auto max-w-6xl px-6">
        <div className="mb-14 max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent-cyan">02 — The wow moment</p>
          <h2 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight text-balance md:text-6xl">
            Two inputs. One trusted plan.
          </h2>
        </div>

        <div className="rounded-[28px] border border-white/10 bg-white/[0.04] p-6 backdrop-blur md:p-10">
          <div className="grid gap-6 md:grid-cols-2">
            <Field label="In case of…" value="I don't check in for 24 hours." accent="cyan" />
            <Field
              label="The app should…"
              value="Ask me if I'm okay. If I don't respond, message my mom."
              accent="coral"
            />
          </div>

          <div className="mt-8 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm">
            <Sparkles className="size-4 text-accent-cyan" />
            <span className="opacity-80">Gemma 4 compiled your safety contract — locally on-device.</span>
            <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.2em] opacity-40">
              gemma-4 · 412 ms
            </span>
          </div>

          <ol className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {STEPS.map((s, i) => (
              <motion.li
                key={s.kind}
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.45, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                className="rounded-2xl border border-white/10 bg-white/[0.05] p-4"
              >
                <div className={`font-mono text-[10px] uppercase tracking-[0.2em] ${COLOR[s.color]}`}>
                  0{i + 1} · {s.kind}
                </div>
                <p className="mt-2 text-[13px] leading-snug">{s.body}</p>
              </motion.li>
            ))}
          </ol>
        </div>

        <a
          href="#gemma"
          className="mt-10 inline-flex items-center gap-2 text-sm text-background/80 transition-colors hover:text-background"
        >
          See how Gemma builds the plan <ArrowRight className="size-4" />
        </a>
      </div>
    </section>
  );
}

function Field({ label, value, accent }: { label: string; value: string; accent: "cyan" | "coral" }) {
  return (
    <div>
      <label className={`font-mono text-[10px] uppercase tracking-[0.22em] ${COLOR[accent]}`}>
        {label}
      </label>
      <div className="mt-2 rounded-2xl border border-white/10 bg-white/[0.04] p-5">
        <p className="font-display text-xl leading-snug md:text-2xl">{value}</p>
      </div>
    </div>
  );
}
