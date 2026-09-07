import type { Metadata } from "next";
import { Demo } from "@/components/Demo";
import { IcoLogo } from "@/components/IcoLogo";

export const metadata: Metadata = {
  title: "In Case Of — live judge demo",
  description:
    "Watch what happens when an expected moment goes unanswered: the person first, then the people they chose, until somebody closes the loop.",
};

export default function DemoPage() {
  return (
    <main className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem)" }}>
      <div style={{ marginBottom: "2rem" }}>
        <a href="/" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }} aria-label="In Case Of Home">
          <IcoLogo size={36} />
        </a>
      </div>
      <p className="eyebrow">Public safe judge demo</p>
      <h1 style={{ fontSize: "clamp(2rem, 5vw, 3rem)" }}>
        What happens when nobody answers
      </h1>
      <p style={{ marginTop: "1.25rem", fontSize: "1.125rem", color: "var(--ico-graphite)" }}>
        Escalation starts with the person themselves, and only then reaches anybody else.
        Acknowledging is not resolving — that distinction is the whole product, so it is worth
        watching for. This page refuses to invent events when the demo stack is unavailable.
      </p>

      <div style={{ marginTop: "2.5rem" }}>
        <Demo />
      </div>

      <hr className="rule" style={{ marginBlock: "3rem" }} />

      <p style={{ color: "var(--ico-graphite)", fontSize: "0.9375rem" }}>
        Demo sessions use synthetic people, short-lived credentials and no private contact
        endpoints. The deployment still uses the real compiler, DynamoDB repositories,
        EventBridge Scheduler, Step Functions workflow and responder authorization path.
      </p>
    </main>
  );
}
