#!/usr/bin/env node
/**
 * Contract consistency gate.
 *
 * docs/API.md is what a human reads; openapi.yaml is what machines read. They drift the
 * moment someone edits one and forgets the other, and a drifted contract in a safety
 * product means a client and a server disagreeing about what an endpoint does.
 *
 * This check fails the build on any of:
 *   1. openapi.yaml does not parse
 *   2. a method + endpoint is documented in one file but not the other
 *   3. a $ref points at a schema file that does not exist
 *   4. any response schema exposes a contactable endpoint (phone number, email, URL)
 *   5. OpenAPI, CDK routes and the Python handler disagree
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

const here = dirname(fileURLToPath(import.meta.url));
const pkgRoot = join(here, "..");
const repoRoot = join(pkgRoot, "..", "..");

const failures = [];
const fail = (msg) => failures.push(msg);

// --- 1. parse -------------------------------------------------------------
const specPath = join(pkgRoot, "openapi.yaml");
let spec;
try {
  spec = parse(readFileSync(specPath, "utf8"));
} catch (err) {
  console.error(`openapi.yaml does not parse: ${err.message}`);
  process.exit(1);
}

// Compare path *shapes*: the two documents may legitimately name a parameter
// differently ({id} vs {memberId}) without disagreeing about the endpoint.
const shape = (p) => p.replace(/\{[^}]+\}/g, "{}");

const HTTP_METHODS = new Set(["get", "post", "put", "patch", "delete"]);
const specRoutes = new Set();
for (const [path, operations] of Object.entries(spec.paths ?? {})) {
  for (const method of Object.keys(operations ?? {})) {
    if (HTTP_METHODS.has(method)) specRoutes.add(`${method.toUpperCase()} ${shape(path)}`);
  }
}

// --- 2. docs/API.md agreement --------------------------------------------
const apiMd = readFileSync(join(repoRoot, "docs", "API.md"), "utf8");
const documented = new Set();
for (const line of apiMd.split("\n")) {
  const m = line.match(/^\s*(GET|POST|PUT|PATCH|DELETE)\s+(\/\S*)/);
  if (m) documented.add(`${m[1]} ${shape(m[2])}`);
}

if (documented.size === 0) fail("docs/API.md lists no endpoints — the check would be vacuous");

for (const p of documented) {
  if (!specRoutes.has(p)) fail(`documented in docs/API.md but missing from openapi.yaml: ${p}`);
}
for (const p of specRoutes) {
  if (!documented.has(p)) fail(`in openapi.yaml but undocumented in docs/API.md: ${p}`);
}

// --- 3. deployed and handled route agreement -----------------------------
const apiTs = readFileSync(join(repoRoot, "infra", "cdk", "lib", "constructs", "api.ts"), "utf8");
const deployed = new Set();
for (const match of apiTs.matchAll(
  /\["([^"]+)",\s*apigw\.HttpMethod\.(GET|POST|PUT|PATCH|DELETE)\]/g,
)) {
  deployed.add(`${match[2]} ${shape(match[1])}`);
}

const apiPy = readFileSync(join(repoRoot, "services", "handlers", "api.py"), "utf8");
const handled = new Set();
for (const match of apiPy.matchAll(/route == "(GET|POST|PUT|PATCH|DELETE) ([^"]+)"/g)) {
  handled.add(`${match[1]} ${shape(match[2])}`);
}
// Demo routes are deliberately a mapping onto the authenticated handlers. Count the
// mapping keys as handled routes; their values are already found in the ordinary route
// comparisons below.
for (const match of apiPy.matchAll(/^\s*"(GET|POST|PUT|PATCH|DELETE) ([^"]+)":/gm)) {
  handled.add(`${match[1]} ${shape(match[2])}`);
}

for (const route of specRoutes) {
  if (!deployed.has(route)) fail(`in openapi.yaml but not deployed by CDK: ${route}`);
  if (!handled.has(route)) fail(`in openapi.yaml but not handled by services/handlers/api.py: ${route}`);
}
for (const route of deployed) {
  if (!specRoutes.has(route)) fail(`deployed by CDK but absent from openapi.yaml: ${route}`);
}
for (const route of handled) {
  if (!specRoutes.has(route)) fail(`handled by services/handlers/api.py but absent from openapi.yaml: ${route}`);
}

// --- 4. $ref targets exist ------------------------------------------------
const refs = new Set();
const collectRefs = (node) => {
  if (Array.isArray(node)) return node.forEach(collectRefs);
  if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) {
      if (k === "$ref" && typeof v === "string" && !v.startsWith("#")) refs.add(v);
      else collectRefs(v);
    }
  }
};
collectRefs(spec);

for (const ref of refs) {
  const target = resolve(pkgRoot, ref.split("#")[0]);
  if (!existsSync(target)) fail(`$ref points at a missing file: ${ref}`);
}

// --- 5. no contactable endpoint may be returned ---------------------------
// Mirrors the Python contract test. The rule is the same on both sides of the wire:
// the API must not hand a client a way to contact someone directly.
const FORBIDDEN = new Set(["phone", "phonenumber", "msisdn", "email", "endpoint", "callbackurl"]);
const scanProps = (node, path) => {
  if (Array.isArray(node)) return node.forEach((n, i) => scanProps(n, `${path}[${i}]`));
  if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) {
      if (k === "properties" && v && typeof v === "object") {
        for (const prop of Object.keys(v)) {
          if (FORBIDDEN.has(prop.toLowerCase().replace(/[_-]/g, ""))) {
            fail(`schema at ${path} exposes a contactable endpoint: "${prop}"`);
          }
        }
      }
      scanProps(v, `${path}.${k}`);
    }
  }
};
scanProps(spec.paths ?? {}, "paths");

// --- report ---------------------------------------------------------------
if (failures.length) {
  console.error("Contract check FAILED:\n");
  for (const f of failures) console.error(`  • ${f}`);
  process.exit(1);
}

console.log(
  `contracts: ${specRoutes.size} method+path routes; docs, CDK and handler agree; ` +
    `${refs.size} external $ref(s) resolve; no contactable endpoints exposed`,
);
