import type { NextConfig } from "next";

/**
 * DocuMindAI - frontend Next.js config.
 *
 * NOTE: Do NOT set `distDir` to a path outside the project root.
 * Next.js 16 + Turbopack validates `distDirRoot` and refuses to start
 * if it navigates above the project (e.g. ../../../../../tmp/next-build2).
 * Leave `distDir` unset to use the default `.next/` inside the project.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
