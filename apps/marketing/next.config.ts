import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  // Next 16 writes its own CLAUDE.md and AGENTS.md into the app directory. A scoped
  // instruction file here would load for any work under apps/ and compete with the
  // repository's own rules, which are deliberate and reviewed. Off.
  agentRules: false,
};

export default nextConfig;
