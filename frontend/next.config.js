/** @type {import('next').NextConfig} */
// DocuMindAI - frontend Next.js config (JS shim).
// Next.js 16 prefers next.config.ts when both exist; this mirrors it.
// NOTE: Do NOT set distDir to a path that navigates outside the project root.
// Next 16 / Turbopack validates distDirRoot and refuses to start if it does.
const nextConfig = {
  reactStrictMode: true,
};
module.exports = nextConfig;
