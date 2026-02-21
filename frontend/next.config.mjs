/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for Docker multi-stage build (Dockerfile copies .next/standalone)
  output: "standalone",
};

export default nextConfig;
