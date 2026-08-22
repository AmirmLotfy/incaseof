#!/usr/bin/env node
/**
 * Generates the web CSS custom properties and the Android Kotlin colour object
 * from tokens.json.
 *
 * Both platforms are generated from one source so a palette change cannot land on
 * the web and silently miss Android. CI runs this with --check and fails on drift.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const pkgRoot = join(here, "..");
const repoRoot = join(pkgRoot, "..", "..");

const tokens = JSON.parse(readFileSync(join(pkgRoot, "tokens.json"), "utf8"));

const BANNER_HASH = "# GENERATED FILE - edit packages/design-tokens/tokens.json instead.";
const BANNER_SLASH = "// GENERATED FILE - edit packages/design-tokens/tokens.json instead.";

const entries = (obj) => Object.entries(obj).filter(([k]) => !k.startsWith("$"));

function css() {
  const light = entries(tokens.light)
    .map(([k, v]) => `  --ico-${k}: ${v.hex};`)
    .join("\n");
  const dark = entries(tokens.dark)
    .map(([k, v]) => `    --ico-${k}: ${v.hex};`)
    .join("\n");
  const on = entries(tokens.onColor)
    .map(([k, v]) => `  --ico-on-${k}: ${v};`)
    .join("\n");
  const shape = entries(tokens.shape)
    .map(([k, v]) => `  --ico-radius-${k}: ${v}px;`)
    .join("\n");
  const space = tokens.spacing.map((v, i) => `  --ico-space-${i + 1}: ${v}px;`).join("\n");

  return `/* ${BANNER_SLASH.slice(3)} */

:root {
${light}
${on}
${shape}
${space}
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
${dark}
  }
}

:root[data-theme="dark"] {
${entries(tokens.dark).map(([k, v]) => `  --ico-${k}: ${v.hex};`).join("\n")}
}
`;
}

function kotlin() {
  const toKt = (hex) => `Color(0xFF${hex.slice(1).toUpperCase()})`;
  const block = (name, set) =>
    `val ${name} = IcoColors(\n` +
    entries(set).map(([k, v]) => `    ${k} = ${toKt(v.hex)},`).join("\n") +
    `\n)`;

  const fields = [...new Set([...entries(tokens.light), ...entries(tokens.dark)].map(([k]) => k))];

  return `${BANNER_SLASH}
package com.incaof.app.core.design

import androidx.compose.ui.graphics.Color

/**
 * In Case of colour tokens.
 *
 * Signal takes Ink text, never white: white on Signal Orange measures 3.52:1 and fails
 * WCAG AA. Stone is a decorative rule only and must never carry state.
 */
data class IcoColors(
${fields.map((f) => `    val ${f}: Color = Color.Unspecified,`).join("\n")}
)

${block("IcoLightColors", tokens.light)}

${block("IcoDarkColors", tokens.dark)}

object IcoOnColor {
${entries(tokens.onColor).map(([k, v]) => `    val ${k} = ${toKt(v)}`).join("\n")}
}

object IcoShape {
${entries(tokens.shape).map(([k, v]) => `    const val ${k} = ${v}`).join("\n")}
}
`;
}

const outputs = [
  [join(pkgRoot, "tokens.css"), css()],
  [
    join(repoRoot, "android/app/src/main/java/com/incaof/app/core/design/Tokens.kt"),
    kotlin(),
  ],
];

const check = process.argv.includes("--check");
let drifted = 0;

for (const [path, content] of outputs) {
  if (check) {
    let current = "";
    try {
      current = readFileSync(path, "utf8");
    } catch {
      current = "";
    }
    if (current !== content) {
      console.error(`DRIFT: ${path} does not match tokens.json`);
      drifted++;
    }
  } else {
    writeFileSync(path, content);
    console.log(`wrote ${path}`);
  }
}

if (check) {
  if (drifted) {
    console.error(
      `\n${drifted} generated file(s) out of date. Run: npm run tokens -w @incaseof/design-tokens`,
    );
    process.exit(1);
  }
  console.log("design tokens: web and Android agree with tokens.json");
}
