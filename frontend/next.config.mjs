/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Local development only: proxy the backend routes to :8000 so relative
    // /api/... and /auth/... paths work when running `next dev` on :3000.
    // In production (Vercel), vercel.json handles the same-origin proxy, so no
    // rewrite is emitted into the build.
    if (process.env.NODE_ENV === "production") return [];
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/auth/:path*",
        destination: "http://localhost:8000/auth/:path*",
      },
      {
        source: "/webhooks/:path*",
        destination: "http://localhost:8000/webhooks/:path*",
      },
    ];
  },
};

export default nextConfig;
