import type { Metadata } from "next";
import { Demo } from "@/components/Demo";

export const metadata: Metadata = {
  title: "In Case of — walkthrough",
  description:
    "Watch what happens when an expected moment goes unanswered: the person first, then the people they chose, until somebody closes the loop.",
};

export default function DemoPage() {
  return (
    <main className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem)" }}>
      <p className="eyebrow">In Case of</p>
      <h1 style={{ fontSize: "clamp(2rem, 5vw, 3rem)" }}>
        What happens when nobody answers
      </h1>
      <p style={{ marginTop: "1.25rem", fontSize: "1.125rem", color: "var(--ico-graphite)" }}>
        Escalation starts with the person themselves, and only then reaches anybody else.
        Acknowledging is not resolving — that distinction is the whole product, so it is worth
        watching for.
      </p>

      <div style={{ marginTop: "2.5rem" }}>
        <Demo />
      </div>

      <hr className="rule" style={{ marginBlock: "3rem" }} />

      <p style={{ color: "var(--ico-graphite)", fontSize: "0.9375rem" }}>
        The deterministic core behind this is tested end to end in{" "}
        <code className="mono">services/tests/slice/</code> — plan created, moment missed,
        alert opened, Circle contacted, claimed, resolved, with the same conditional writes
        that make duplicate contacts impossible.
      </p>
    </main>
  );
}
