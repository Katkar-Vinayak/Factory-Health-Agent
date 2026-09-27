import type { NextConfig } from "next";

// Determine backend API destination for Next.js same-origin proxy rewrites.
// Prefer server-side BACKEND_API_URL, fallback to NEXT_PUBLIC_API_URL, then local default.
const backendUrl = (
  process.env.BACKEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
