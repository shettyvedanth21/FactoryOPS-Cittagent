import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/device/:path*",
        destination: "http://device-service:8000/:path*",
      },
      {
        source: "/backend/data/:path*",
        destination: "http://data-service:8081/:path*",
      },
      {
        source: "/backend/rule-engine/:path*",
        destination: "http://rule-engine-service:8002/:path*",
      },

      // analytics-service
      {
        source: "/backend/analytics/:path*",
        destination: "http://analytics-service:8003/:path*",
      },

      // ✅ data-export-service
      {
        source: "/backend/data-export/:path*",
        destination: "http://data-export-service:8080/:path*",
      },

      // reporting-service
      {
        source: "/api/reports/:path(.*)",
        destination: "http://reporting-service:8085/api/reports/:path(.*)",
      },
    ];
  },
};

export default nextConfig;