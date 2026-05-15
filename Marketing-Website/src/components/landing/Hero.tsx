import { motion } from "motion/react";
import { ArrowRight, Download, Github, Play, ShieldCheck } from "lucide-react";
import heroPhone from "@/assets/hero-phone.png";

const TRUST = [
  "Gemma 4 on-device",
  "No hidden monitoring",
  "User approves every action",
  "Built for Android first",
];

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pt-32 pb-24 md:pt-40 md:pb-28">
      <div className="absolute inset-0 -z-10 gradient-hero" />
      <div className="absolute inset-0 -z-10 gradient-bloom opacity-80" />
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-16 px-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 rounded-full border hairline bg-card/60 px-3 py-1.5 backdrop-blur"
          >
            <span className="size-1.5 rounded-full bg-accent-coral blink" />
            <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Built for Kaggle Gemma 4 Good Hackathon
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
            className="font-display mt-6 text-5xl font-semibold leading-[0.98] tracking-tight text-balance md:text-7xl"
          >
            A safety agent for the moments
            <span className="text-muted-foreground"> you can&apos;t respond.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.12, ease: [0.16, 1, 0.3, 1] }}
            className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground text-pretty"
          >
            <span className="text-foreground">In Case of</span> turns simple sentences like{" "}
            <em className="not-italic text-foreground">
              &ldquo;if I don&apos;t check in for 24 hours, alert my mom&rdquo;
            </em>{" "}
            into a local-first, user-approved Android safety plan powered by Gemma 4.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="mt-9 flex flex-wrap items-center gap-3"
          >
            <a
              href="/downloads/in-case-of-v1.apk"
              download
              className="group inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3.5 text-[15px] font-medium text-background shadow-[0_10px_40px_-10px_oklch(0.16_0.06_280/35%)] transition-transform hover:-translate-y-0.5 active:scale-[0.98]"
            >
              <Download className="size-4" />
              Download Android APK
              <ArrowRight className="size-4 opacity-60 transition-transform group-hover:translate-x-0.5" />
            </a>
            <a
              href="#demo"
              className="inline-flex items-center gap-2 rounded-full border hairline bg-card/70 px-5 py-3.5 text-[15px] font-medium backdrop-blur transition-colors hover:bg-card"
            >
              <Play className="size-4" />
              Watch 3-min Demo
            </a>
            <a
              href="#resources"
              className="inline-flex items-center gap-2 rounded-full px-3 py-3.5 text-[15px] font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <Github className="size-4" />
              View GitHub
            </a>
          </motion.div>

          <motion.ul
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="mt-10 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground"
          >
            {TRUST.map((t) => (
              <li key={t} className="inline-flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-accent-violet" />
                {t}
              </li>
            ))}
          </motion.ul>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="relative mx-auto w-full max-w-[520px]"
        >
          <div className="absolute -inset-10 -z-10 rounded-[3rem] bg-gradient-to-br from-accent-cyan/30 via-transparent to-accent-violet/25 blur-3xl" />
          <img
            src={heroPhone}
            alt="In Case of Android app showing an active safety case"
            width={1024}
            height={1024}
            className="relative w-full drop-shadow-[0_40px_60px_oklch(0.16_0.06_280/25%)]"
          />
          {/* Floating workflow chips */}
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
            className="absolute -left-2 top-12 hidden rounded-2xl border hairline bg-card/90 p-3 shadow-soft backdrop-blur md:block"
          >
            <div className="text-[10px] font-mono uppercase tracking-widest text-accent-violet">Trigger</div>
            <div className="mt-1 text-sm font-medium">No check-in · 24h</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7, duration: 0.6 }}
            className="absolute -right-4 bottom-24 hidden rounded-2xl border hairline bg-card/90 p-3 shadow-soft backdrop-blur md:block"
          >
            <div className="text-[10px] font-mono uppercase tracking-widest text-accent-coral">Action</div>
            <div className="mt-1 text-sm font-medium">SMS prepared · awaiting tap</div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
