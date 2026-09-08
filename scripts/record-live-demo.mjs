#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const baseUrl = (process.env.ICO_RECORD_BASE_URL || "https://incaof.com").replace(/\/$/, "");
const outputDir = "submission/video/remake/captures";
const outputPath = `${outputDir}/live-demo-flow.webm`;
const events = [];
const startedAt = Date.now();

function mark(label) {
  events.push({ label, seconds: Number(((Date.now() - startedAt) / 1000).toFixed(3)) });
  console.log(`${events.at(-1).seconds}s ${label}`);
}

async function pause(page, milliseconds) {
  await page.waitForTimeout(milliseconds);
}

async function installCursor(page) {
  await page.evaluate(() => {
    const existing = document.querySelector("[data-demo-cursor]");
    if (existing) return;
    const cursor = document.createElement("div");
    cursor.dataset.demoCursor = "true";
    cursor.setAttribute("aria-hidden", "true");
    Object.assign(cursor.style, {
      position: "fixed",
      left: "48px",
      top: "48px",
      width: "22px",
      height: "22px",
      border: "3px solid #f4f1ea",
      borderRadius: "999px",
      background: "#e85b2a",
      boxShadow: "0 2px 10px rgba(0,0,0,.38)",
      pointerEvents: "none",
      zIndex: "2147483647",
      transition: "left .32s ease, top .32s ease, transform .16s ease",
    });
    document.body.append(cursor);
    window.addEventListener("pointermove", (event) => {
      cursor.style.left = `${event.clientX - 11}px`;
      cursor.style.top = `${event.clientY - 11}px`;
    });
    window.addEventListener("pointerdown", () => { cursor.style.transform = "scale(.72)"; });
    window.addEventListener("pointerup", () => { cursor.style.transform = "scale(1)"; });
  });
}

async function click(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 18 });
  await pause(page, 500);
  await locator.click();
}

await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  colorScheme: "light",
  recordVideo: { dir: outputDir, size: { width: 1920, height: 1080 } },
});
const page = await context.newPage();
const video = page.video();

try {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.getByRole("main").waitFor();
  await installCursor(page);
  mark("landing-ready");
  await pause(page, 3500);
  for (let index = 0; index < 4; index += 1) {
    await page.mouse.wheel(0, 360);
    await pause(page, 650);
  }
  await pause(page, 1500);

  await page.goto(`${baseUrl}/demo`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Compile the plan" }).waitFor();
  await installCursor(page);
  mark("demo-ready");
  await pause(page, 2300);
  await click(page, page.getByRole("button", { name: "Compile the plan" }));
  await page.getByRole("button", { name: "Save this draft" }).waitFor({ timeout: 45_000 });
  mark("preview-ready");
  await pause(page, 8000);
  await click(page, page.getByRole("button", { name: "Save this draft" }));
  await page.getByRole("button", { name: "Test this plan" }).waitFor({ timeout: 20_000 });
  mark("draft-saved");
  await pause(page, 3500);
  await click(page, page.getByRole("button", { name: "Test this plan" }));
  mark("drill-started");
  await pause(page, 5000);

  const responderLink = page.getByRole("link", { name: "Open responder link" });
  await responderLink.waitFor({ timeout: 120_000 });
  await page.getByText("STATE CIRCLE ESCALATION", { exact: false }).waitFor({ timeout: 120_000 });
  mark("circle-escalation-visible");
  await pause(page, 9000);
  const responderHref = await responderLink.getAttribute("href");
  if (!responderHref) throw new Error("The deployed drill did not return a responder URL.");

  await page.goto(responderHref, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /hasn.t responded/i }).waitFor({ timeout: 30_000 });
  await installCursor(page);
  mark("responder-room-ready");
  await pause(page, 6500);
  await click(page, page.getByRole("button", { name: /I.m checking/i }));
  await page.getByRole("heading", { name: /You.re checking/i }).waitFor({ timeout: 20_000 });
  mark("lease-created");
  await pause(page, 6500);
  await click(page, page.getByRole("button", { name: /I reached .*all okay/i }));
  await page.getByRole("heading", { name: "This check is closed" }).waitFor({ timeout: 20_000 });
  mark("alert-resolved");
  await pause(page, 6500);
} finally {
  await page.close();
  await context.close();
  await browser.close();
}

const recordedPath = await video.path();
await rename(recordedPath, outputPath);
const sha256 = createHash("sha256").update(await readFile(outputPath)).digest("hex");
await writeFile(
  `${outputDir}/live-demo-flow.json`,
  `${JSON.stringify({ capturedAt: new Date().toISOString(), baseUrl, outputPath, sha256, events }, null, 2)}\n`,
);
console.log(`Recorded ${outputPath}`);
