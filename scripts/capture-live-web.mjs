#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const manifestPath = "submission/release-evidence.json";
const outputDir = "submission/screenshots";
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const baseUrl = (process.env.ICO_CAPTURE_BASE_URL || manifest.urls?.marketing || "").replace(/\/$/, "");
const mode = process.env.ICO_CAPTURE_MODE || "final";

function requireCondition(condition, message) {
  if (!condition) throw new Error(message);
}

function publicSourceUrl(rawUrl) {
  const url = new URL(rawUrl);
  url.search = "";
  url.hash = "";
  url.pathname = url.pathname.replace(/^\/(r|i)\/[^/]+/, "/$1/[redacted]");
  return url.toString();
}

requireCondition(mode === "final" || mode === "rehearsal", "ICO_CAPTURE_MODE must be final or rehearsal");
requireCondition(baseUrl, "Set ICO_CAPTURE_BASE_URL or record urls.marketing in the release manifest");
const parsedBase = new URL(baseUrl);
if (mode === "final") {
  requireCondition(parsedBase.protocol === "https:", "final captures require HTTPS");
  requireCondition(
    parsedBase.hostname === "incaof.com" || parsedBase.hostname === "www.incaof.com",
    "final captures require the canonical incaof.com host",
  );
  requireCondition(
    manifest.canary?.runtimeReadyForRequest === true,
    "final captures require a successful AgentCore runtime canary",
  );
}

await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const captured = [];

async function screenshot(page, filename) {
  const path = `${outputDir}/${filename}`;
  await page.screenshot({ path, fullPage: true, animations: "disabled" });
  const sha256 = createHash("sha256").update(await readFile(path)).digest("hex");
  captured.push({ filename, sha256, sourceUrl: publicSourceUrl(page.url()) });
}

async function openChecked(page, url) {
  const response = await page.goto(url, { waitUntil: "domcontentloaded" });
  requireCondition(response?.ok(), `${url} returned ${response?.status() ?? "no response"}`);
}

try {
  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
    colorScheme: "light",
  });
  const page = await desktop.newPage();
  await openChecked(page, `${baseUrl}/`);
  await page.getByRole("main").waitFor();
  await screenshot(page, "marketing-desktop.png");

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    colorScheme: "light",
  });
  const mobilePage = await mobile.newPage();
  await openChecked(mobilePage, `${baseUrl}/`);
  await mobilePage.getByRole("main").waitFor();
  await screenshot(mobilePage, "marketing-mobile.png");
  await mobile.close();

  await openChecked(page, `${baseUrl}/demo`);
  await page.getByText("Live AWS demo.", { exact: false }).waitFor();
  await page.getByRole("button", { name: "Compile the plan" }).click();
  await page.getByText("AgentCore preview", { exact: false }).waitFor({ timeout: 45_000 });
  requireCondition((await page.getByRole("alert").count()) === 0, "the live compiler returned an error");
  await screenshot(page, "web-plan-preview.png");

  await page.getByText("Developer Trace", { exact: true }).click();
  await page.getByText("Redacted evidence returned", { exact: false }).waitFor();
  await screenshot(page, "developer-trace-redacted.png");

  await page.getByRole("button", { name: "Save this draft" }).click();
  await page.getByRole("button", { name: "Test this plan" }).waitFor({ timeout: 20_000 });
  await page.getByRole("button", { name: "Test this plan" }).click();
  const responderLink = page.getByRole("link", { name: "Open responder link" });
  await responderLink.waitFor({ timeout: 120_000 });
  await page.getByText("STATE CIRCLE ESCALATION", { exact: false }).waitFor({ timeout: 120_000 });
  await screenshot(page, "audit-timeline.png");

  const responderHref = await responderLink.getAttribute("href");
  requireCondition(responderHref, "the live demo did not return a responder link");
  const responderUrl = new URL(responderHref);
  requireCondition(responderUrl.protocol === "https:" || mode === "rehearsal", "responder link is not HTTPS");
  requireCondition(
    mode === "rehearsal" ||
      responderUrl.hostname === "incaof.com" ||
      responderUrl.hostname === "www.incaof.com",
    "responder link is not on the canonical host",
  );

  const responder = await desktop.newPage();
  await openChecked(responder, responderHref);
  await responder.getByRole("heading", { name: /hasn.t responded/i }).waitFor();
  await screenshot(responder, "responder-claim.png");
  await responder.getByRole("button", { name: /I.m checking/i }).click();
  await responder.getByRole("heading", { name: /You.re checking/i }).waitFor();
  await screenshot(responder, "responder-lease.png");
  await responder.getByRole("button", { name: /I reached .*all okay/i }).click();
  await responder.getByRole("heading", { name: "This check is closed" }).waitFor();
  await screenshot(responder, "responder-resolved.png");

  await responder.close();
  await desktop.close();
} finally {
  await browser.close();
}

const provenance = {
  capturedAt: new Date().toISOString(),
  mode,
  baseUrl,
  sourceCommit: execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim(),
  captures: captured,
  statement:
    "Browser captures came from rendered live pages. No request interception or fixture substitution was used.",
};
await writeFile(`${outputDir}/web-provenance.json`, `${JSON.stringify(provenance, null, 2)}\n`);
console.log(
  `Captured ${captured.length} live web screenshots and wrote ${outputDir}/web-provenance.json`,
);
