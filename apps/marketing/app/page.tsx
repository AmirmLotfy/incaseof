import type { Metadata } from "next";
import { ContextTiers } from "@/components/ContextTiers";
import { Contrast, Mechanism, Row, Said } from "@/components/Sections";
import { TimelineDevice } from "@/components/Timeline";

export const metadata: Metadata = {
  title: "In Case of — Someone notices.",
  description:
    "Tell In Case of what should happen. If it doesn’t, it knows who to reach and when to keep going. No continuous location. No always-on microphone.",
};

/**
 * incaof.com — home. Build contract §73–§84.
 *
 * Every claim on this page is one the product actually makes. There are no metrics, no
 * testimonials, no company logos and no download counts, because we have none of those
 * things and inventing them would be the fastest way to make a safety product untrustworthy.
 */
export default function Home() {
  return (
    <>
      <Header />

      {/* A named landmark, so a screen reader can skip the header to reach this. */}
      <main id="main">

      {/* §74. Type left, the product's own timeline right. No phone in a gradient cloud. */}
      <section className="shell" style={{ paddingTop: "clamp(3rem, 7vw, 5rem)" }}>
        <div
          style={{
            display: "grid",
            gap: "clamp(2.5rem, 5vw, 4rem)",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 24rem), 1fr))",
            alignItems: "center",
          }}
        >
          <div>
            <h1>Someone notices.</h1>
            <p style={{ marginTop: "1.5rem", fontSize: "1.25rem" }}>
              Tell In Case of what should happen. If it doesn’t, it knows who to reach and
              when to keep going.
            </p>

            <div
              style={{
                marginTop: "2rem",
                display: "flex",
                gap: "1.25rem",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <a className="cta" href="#beta">
                Join the Android beta
              </a>
              <a className="cta cta--quiet" href="#how">
                See how it works
              </a>
            </div>

            <p
              className="mono"
              style={{
                marginTop: "2rem",
                fontSize: "0.8125rem",
                color: "var(--ico-graphite)",
              }}
            >
              No continuous location. No always-on microphone.
            </p>
          </div>

          <TimelineDevice />
        </div>
      </section>

      <hr className="rule" />

      {/* §76 */}
      <section className="shell">
        <h2>It watches the plan. Not you.</h2>
        <Contrast
          needs={["A time", "A plan", "Your Circle", "Your permissions"]}
          doesNotNeed={[
            "Your location all day",
            "Your microphone all day",
            "A camera",
            "Someone watching a dashboard",
          ]}
        />
      </section>

      <hr className="rule" />

      {/* §77 */}
      <section className="shell" id="how">
        <h2>How it works</h2>
        <Mechanism />
      </section>

      <hr className="rule" />

      {/* §78. Alternating editorial rows, deliberately not a four-card grid. */}
      <section className="shell">
        <h2>When it helps</h2>
        <div style={{ display: "grid", gap: "clamp(2.5rem, 6vw, 4.5rem)", marginTop: "3rem" }}>
          <Row
            eyebrow="Living alone"
            title="A check that happens whether or not anyone remembers"
            aside={<Said>“Check on me every evening.”</Said>}
          >
            <p>
              Nothing happens while everything is normal. The evening it doesn’t, In Case of
              starts with you — and only then with anyone else.
            </p>
          </Row>

          <Row
            eyebrow="Getting home"
            title="Someone knows you were expected"
            flip
            aside={<Said>“I should be back before midnight.”</Said>}
          >
            <p>
              A one-off expectation for one night. It closes the moment you say you’re home,
              and it doesn’t become a habit you have to maintain.
            </p>
          </Row>

          <Row
            eyebrow="Out solo"
            title="Cover for the hours nobody can see you"
            aside={<Said>“I’m hiking until six.”</Said>}
          >
            <p>
              You choose how much lateness is normal before anything happens. Being an hour
              behind on a hill is not an emergency, and the plan can say so.
            </p>
          </Row>

          <Row
            eyebrow="Recovery"
            title="Repeated checks, without someone sitting up all night"
            flip
            aside={<Said>“Check every three hours tonight.”</Said>}
          >
            <p>
              The people you chose are contacted only if a check goes unanswered — so nobody
              has to stay awake watching for one.
            </p>
          </Row>
        </div>
      </section>

      <hr className="rule" />

      {/* §79 */}
      <section className="shell">
        <div
          style={{
            display: "grid",
            gap: "clamp(2rem, 5vw, 4rem)",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 22rem), 1fr))",
            alignItems: "start",
          }}
        >
          <div>
            <h2>The right person. Only when they’re needed.</h2>
            <p style={{ marginTop: "1.5rem", color: "var(--ico-graphite)" }}>
              Your Circle isn’t watching you. They hear from In Case of when something you
              expected didn’t happen — and they’re told what has already been tried, so they
              know whether to worry.
            </p>
            <p style={{ marginTop: "1rem", color: "var(--ico-graphite)" }}>
              They don’t need the app. A private link works from a message, and it only ever
              opens the one check it was sent for.
            </p>
          </div>

          <ResponderPreview />
        </div>
      </section>

      <hr className="rule" />

      {/* §80 */}
      <section className="shell">
        <h2>Share later. Only if you chose to.</h2>
        <p style={{ marginTop: "1.5rem", color: "var(--ico-graphite)" }}>
          Nothing about you is shared by default. You decide in advance which signals can
          become visible, and at which point.
        </p>
        <ContextTiers />
      </section>

      <hr className="rule" />

      {/* §81. The trust section. A far stronger claim than any badge would be. */}
      <section className="shell">
        <h2>Judgment where it’s useful. Rules where they matter.</h2>
        <p style={{ marginTop: "1.5rem", color: "var(--ico-graphite)" }}>
          In Case of uses a language model to understand what people mean. Timers,
          permissions, contacts and escalation rules stay deterministic.
        </p>

        <div
          style={{
            display: "grid",
            gap: "clamp(1.5rem, 4vw, 3rem)",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 16rem), 1fr))",
            marginTop: "3rem",
          }}
        >
          <Boundary
            step="Understand"
            body="“I’m okay, I fell asleep.”"
            result="Read as a clear confirmation"
          />
          <Boundary
            step="Authorise"
            body="Can this action happen, for this person, right now?"
            result="Checked in code, not in a prompt"
          />
          <Boundary
            step="Execute"
            body="Close the check and stop the ladder"
            result="Done by the workflow, not the model"
          />
        </div>

        <p style={{ marginTop: "2.5rem", color: "var(--ico-graphite)" }}>
          The model can suggest contacting someone. It cannot name a phone number — there is
          no way to express one. If it’s unavailable, your plan runs exactly the same.
        </p>
      </section>

      <hr className="rule" />

      {/* §82 */}
      <section className="shell">
        <h2>Nothing happens invisibly.</h2>
        <p style={{ marginTop: "1.5rem", color: "var(--ico-graphite)" }}>
          Every check keeps a record of what was tried, who was contacted, and who closed
          it.
        </p>

        <div className="scroller" style={{ marginTop: "2.5rem" }}>
          <ol
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              minWidth: "22rem",
              borderTop: "1px solid var(--ico-stone)",
            }}
          >
            {[
              ["21:00", "Check requested"],
              ["21:10", "Reminder sent"],
              ["21:20", "Message sent"],
              ["21:23", "Maya contacted"],
              ["21:25", "Maya checking"],
              ["21:31", "Resolved by Maya"],
            ].map(([time, event]) => (
              <li
                key={time}
                style={{
                  display: "grid",
                  gridTemplateColumns: "5rem 1fr",
                  gap: "1rem",
                  padding: "0.65rem 0",
                  borderBottom: "1px solid var(--ico-stone)",
                }}
              >
                <span className="mono" style={{ color: "var(--ico-graphite)" }}>
                  {time}
                </span>
                <span>{event}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* §83. A Signal Orange rule across the top — never an orange background. */}
      <section id="beta" style={{ borderTop: "3px solid var(--ico-signal)" }}>
        <div className="shell">
          <h2>Set the plan once. Get on with your life.</h2>
          <p style={{ marginTop: "1.5rem", color: "var(--ico-graphite)" }}>
            In Case of is in development for the Agents for Humans hackathon. The Android
            beta isn’t open yet.
          </p>
          <div
            style={{
              marginTop: "2rem",
              display: "flex",
              gap: "1.25rem",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <a className="cta" href="https://github.com/AmirmLotfy/incaseof">
              View the project on GitHub
            </a>
          </div>
        </div>
      </section>
      </main>

      <Footer />
    </>
  );
}

function Header() {
  return (
    <header className="shell" style={{ paddingBlock: "1.5rem" }}>
      <nav
        aria-label="Main"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 600, letterSpacing: "-0.02em" }}>in case of</span>
        <span style={{ display: "flex", gap: "1.5rem", alignItems: "center" }}>
          <a href="#how" style={linkStyle}>
            How it works
          </a>
          <a href="#beta" style={linkStyle}>
            The project
          </a>
        </span>
      </nav>
    </header>
  );
}

function Footer() {
  return (
    <footer
      className="shell"
      style={{ paddingBlock: "3rem", borderTop: "1px solid var(--ico-stone)" }}
    >
      <p style={{ fontWeight: 600 }}>in case of</p>
      <p style={{ color: "var(--ico-graphite)", marginTop: "0.25rem" }}>Someone notices.</p>

      <p
        style={{
          marginTop: "2rem",
          color: "var(--ico-graphite)",
          fontSize: "0.9375rem",
          maxWidth: "var(--prose)",
        }}
      >
        In Case of is not an emergency service. It coordinates the plans and trusted contacts
        you choose, and is not a substitute for local emergency services, medical care or
        professional monitoring.
      </p>

      <p
        className="mono"
        style={{ marginTop: "2rem", fontSize: "0.75rem", color: "var(--ico-graphite)" }}
      >
        © 2026 In Case of
      </p>
    </footer>
  );
}

function Boundary({
  step,
  body,
  result,
}: {
  step: string;
  body: string;
  result: string;
}) {
  return (
    <div style={{ borderTop: "2px solid var(--ico-ink)", paddingTop: "1rem" }}>
      <p className="eyebrow" style={{ marginBottom: "0.75rem" }}>
        {step}
      </p>
      <p style={{ color: "var(--ico-ink)" }}>{body}</p>
      <p style={{ marginTop: "0.75rem", color: "var(--ico-graphite)", fontSize: "0.9375rem" }}>
        ↳ {result}
      </p>
    </div>
  );
}

/** A still of the responder surface, so the claim above it is visible rather than asserted. */
function ResponderPreview() {
  return (
    <div
      style={{
        border: "1px solid var(--ico-stone)",
        borderRadius: "20px",
        background: "var(--ico-surface)",
        padding: "1.75rem",
      }}
    >
      <p className="eyebrow">A message to your Circle</p>
      <p style={{ fontSize: "1.25rem", fontWeight: 600, marginTop: "0.5rem" }}>
        Mona hasn’t responded
      </p>
      <p className="mono" style={{ fontSize: "0.8125rem", color: "var(--ico-graphite)", marginTop: "0.5rem" }}>
        Evening check · Expected 9:00 PM
      </p>

      <ul style={{ listStyle: "none", padding: 0, margin: "1.25rem 0 0" }}>
        {[
          ["9:00", "Check requested"],
          ["9:10", "Reminder sent"],
          ["9:20", "Message sent"],
        ].map(([time, event]) => (
          <li key={time} style={{ display: "flex", gap: "1rem", padding: "0.3rem 0" }}>
            <span className="mono" style={{ color: "var(--ico-graphite)", minWidth: "3.5rem" }}>
              {time}
            </span>
            <span style={{ fontSize: "0.9375rem" }}>{event}</span>
          </li>
        ))}
      </ul>

      <p
        style={{
          marginTop: "1.5rem",
          padding: "0.85rem 1rem",
          borderRadius: "12px",
          background: "var(--ico-signal)",
          color: "var(--ico-on-signal)",
          textAlign: "center",
          fontWeight: 500,
        }}
      >
        I’m checking
      </p>
    </div>
  );
}

const linkStyle: React.CSSProperties = {
  color: "var(--ico-ink)",
  textDecoration: "none",
  fontSize: "0.9375rem",
};
