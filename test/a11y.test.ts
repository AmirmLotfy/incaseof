/**
 * Accessibility, checked in a real browser.
 *
 * This is a blocking gate, not an aspiration — `.claude/rules/android.md` says so for the
 * app and `docs/design/DESIGN.md` §68 says so for the web. The people this product is for
 * read it one-handed, at night, sometimes on a cracked phone, sometimes with a screen
 * reader, and always while worried. An interface that is hard to operate under those
 * conditions is not a styling problem.
 *
 * axe finds a real but partial set of problems. What it cannot check — focus order that
 * makes sense, a timeline that reads chronologically, whether a label says something true —
 * is asserted separately below and reviewed by hand.
 */

import assert from "node:assert/strict";
import { after, before, describe, it } from "node:test";
import { spawn, type ChildProcess } from "node:child_process";
import { fileURLToPath } from "node:url";
import { AxeBuilder } from "@axe-core/playwright";
import { chromium, type Browser, type Page } from "playwright";

const PORT = 4321;
const BASE = `http://127.0.0.1:${PORT}`;
const MARKETING_PORT = 4322;
const MARKETING = `http://127.0.0.1:${MARKETING_PORT}`;

/** WCAG 2.2 AA. The floor the design system commits to. */
const STANDARD = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

let server: ChildProcess;
let marketing: ChildProcess;
let browser: Browser;

async function reachable(url: string, attempts = 60): Promise<void> {
  for (let i = 0; i < attempts; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Not up yet.
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`${url} never became reachable`);
}

function serve(app: string, port: number): ChildProcess {
  // `next start`, not `next dev`. Under the dev server hydration does not complete here,
  // so every control stays inert — which made the "claimed state" check silently re-test
  // the unclaimed one and pass. A production build is also what people actually load.
  return spawn("npx", ["next", "start", "--port", String(port)], {
    // fileURLToPath, not .pathname: the repository path contains a space, which .pathname
    // hands back percent-encoded and spawn then treats as a literal directory name.
    cwd: fileURLToPath(new URL(`../apps/${app}`, import.meta.url)),
    stdio: "ignore",
    detached: false,
  });
}

before(async () => {
  server = serve("responder", PORT);
  marketing = serve("marketing", MARKETING_PORT);
  await Promise.all([reachable(BASE), reachable(MARKETING)]);
  browser = await chromium.launch();
});

after(async () => {
  await browser?.close();
  server?.kill("SIGTERM");
  marketing?.kill("SIGTERM");
});

async function newPage(): Promise<Page> {
  // axe-core/playwright refuses a page created straight off the browser.
  const context = await browser.newContext();
  return context.newPage();
}

async function violations(page: Page) {
  const result = await new AxeBuilder({ page }).withTags(STANDARD).analyze();
  return result.violations.map(
    (v) => `${v.id} (${v.impact}) — ${v.help}\n      ${v.nodes[0]?.html?.slice(0, 120)}`,
  );
}

describe("responder web accessibility", () => {
  it("the Incident Room has no WCAG AA violations", async () => {
    const page = await newPage();
    await page.goto(`${BASE}/r/sample`);
    await page.waitForSelector("main");

    const found = await violations(page);
    assert.deepEqual(found, [], `\n    ${found.join("\n    ")}\n`);
    await page.close();
  });

  it("the claimed state has none either", async () => {
    // The state a responder is actually in while deciding what to do, and the one with the
    // countdown — so the one most likely to have a live-region or contrast problem.
    const page = await newPage();
    await page.goto(`${BASE}/r/sample`);
    await page.waitForSelector("main");
    await page.getByRole("button", { name: /checking/i }).click();
    await page.waitForTimeout(300);

    const found = await violations(page);
    assert.deepEqual(found, [], `\n    ${found.join("\n    ")}\n`);
    await page.close();
  });

  it("the invalid-link page has none", async () => {
    const page = await newPage();
    await page.goto(`${BASE}/r/invalid`);
    await page.waitForSelector("main");

    const found = await violations(page);
    assert.deepEqual(found, [], `\n    ${found.join("\n    ")}\n`);
    await page.close();
  });

  it("every control clears the 44px touch floor", async () => {
    // WCAG 2.2 target size, and the reason the Android rules say 48dp. A responder taps
    // this half-awake; a control that needs aim is a control that gets mis-hit.
    const page = await newPage();
    await page.goto(`${BASE}/r/sample`);
    await page.waitForSelector("main");

    const small: string[] = [];
    let checked = 0;

    const measure = async () => {
      for (const control of await page.getByRole("button").all()) {
        const box = await control.boundingBox();
        if (!box) continue;
        checked++;
        const label = (await control.textContent())?.trim() ?? "?";
        if (box.height < 44 || box.width < 44) {
          small.push(`${label}: ${Math.round(box.width)}×${Math.round(box.height)}`);
        }
      }
    };

    await measure();
    // The claimed state carries most of the controls — extend, unable, resolve — so
    // measuring only the unclaimed one would check a single button and call it a pass.
    await page.getByRole("button", { name: /checking/i }).click();
    await page.waitForTimeout(300);
    await measure();

    // One control unclaimed, two claimed. Asserting the count catches the failure mode
    // where the state never advances and this quietly measures the same button twice.
    assert.equal(checked, 3, `measured ${checked} controls, expected 3 across both states`);
    assert.deepEqual(small, [], `controls below 44px: ${small.join(", ")}`);
    await page.close();
  });

  it("the timeline reads in chronological order to a screen reader", async () => {
    // Visual order and DOM order can disagree, and a timeline that reads backwards to
    // TalkBack tells the story in reverse — which is worse than not telling it.
    const page = await newPage();
    await page.goto(`${BASE}/r/sample`);
    await page.waitForSelector("main");

    const times = await page.locator("[data-timeline-at]").evaluateAll((nodes) =>
      nodes.map((n) => n.getAttribute("data-timeline-at") ?? ""),
    );

    assert.ok(times.length > 1, "the sample incident should have a timeline");
    assert.deepEqual(times, [...times].sort(), "timeline is not in chronological DOM order");
    await page.close();
  });

  it("state is never carried by colour alone", async () => {
    // DESIGN.md is explicit: orange means unresolved, and that has to survive both
    // colour-blindness and a greyscale screenshot. Anything painted in a state colour must
    // also say something in words.
    const page = await newPage();
    await page.goto(`${BASE}/r/sample`);
    await page.waitForSelector("main");

    const mute = await page.evaluate(() => {
      const state = ["--ico-signal", "--ico-critical", "--ico-resolved"]
        .map((token) =>
          getComputedStyle(document.documentElement).getPropertyValue(token).trim(),
        )
        .filter(Boolean);

      return [...document.querySelectorAll("*")]
        .filter((node) => {
          const colour = getComputedStyle(node).color;
          const painted = state.some((value) => colour === value);
          const ownText = [...node.childNodes]
            .filter((child) => child.nodeType === Node.TEXT_NODE)
            .map((child) => child.textContent ?? "")
            .join("")
            .trim();
          return painted && ownText.length === 0 && node.children.length === 0;
        })
        .map((node) => node.tagName.toLowerCase());
    });

    assert.deepEqual(mute, [], `state shown only in colour: ${mute.join(", ")}`);
    await page.close();
  });
});

describe("marketing site accessibility", () => {
  for (const [name, path] of [
    ["the home page", "/"],
    ["the demo page", "/demo"],
  ] as const) {
    it(`${name} has no WCAG AA violations`, async () => {
      const page = await newPage();
      await page.goto(`${MARKETING}${path}`);
      await page.waitForSelector("main");

      const found = await violations(page);
      assert.deepEqual(found, [], `\n    ${found.join("\n    ")}\n`);
      await page.close();
    });
  }

  for (const [label, width, height] of [
    ["a small phone", 320, 568],
    ["a phone", 390, 844],
    ["a tablet", 768, 1024],
    ["a laptop", 1440, 900],
  ] as const) {
    it(`does not scroll sideways on ${label}`, async () => {
      // Horizontal overflow is the most common responsive failure and the most annoying:
      // it hides content off an edge with no affordance saying it is there.
      const page = await newPage();
      await page.setViewportSize({ width, height });
      await page.goto(MARKETING);
      await page.waitForSelector("main");

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );

      assert.ok(overflow <= 0, `${overflow}px of horizontal overflow at ${width}px`);
      await page.close();
    });
  }
});
