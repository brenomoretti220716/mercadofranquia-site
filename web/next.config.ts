/** @type {import('next').NextConfig} */

const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});

/**
 * Permite `next/image` buscar uploads na mesma origem que NEXT_PUBLIC_API_URL (ex.: IP da LAN).
 * Sem isso, `/_next/image?url=http://192.168.x.x:4000/...` retorna 400 Bad Request.
 * @returns {import('next/dist/shared/lib/image-config').RemotePattern | null}
 */
function uploadRemotePatternFromPublicApiUrl() {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (!raw || typeof raw !== "string") return null;
  try {
    const u = new URL(raw.trim());
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    /** @type {import('next/dist/shared/lib/image-config').RemotePattern} */
    const pattern: import("next/dist/shared/lib/image-config").RemotePattern = {
      protocol: u.protocol === "https:" ? "https" : "http",
      hostname: u.hostname,
      pathname: "/uploads/**",
      ...(u.port ? { port: u.port } : {}),
    };
    return pattern;
  } catch {
    return null;
  }
}

const envUploadPattern = uploadRemotePatternFromPublicApiUrl();

const nextConfig = {
  // Enable standalone output for Docker
  output: "standalone",

  // Enable React production mode
  reactStrictMode: true,

  // Optimize compiler for better tree-shaking and smaller bundles
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },

  // Webpack optimizations
  webpack: (config: any, { isServer }: { isServer: boolean }) => {
    // Optimize bundle size
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        moduleIds: "deterministic",
        runtimeChunk: "single",
      };
    }

    return config;
  },

  images: {
    remotePatterns: [
      ...(envUploadPattern ? [envUploadPattern] : []),
      {
        protocol: "http",
        hostname: "localhost",
        port: "4000",
        pathname: "/uploads/**",
      },
      {
        protocol: "http",
        hostname: "192.168.15.190",
        port: "4000",
        pathname: "/uploads/**",
      },
      {
        protocol: "http",
        hostname: "host.docker.internal",
        port: "4000",
        pathname: "/uploads/**",
      },
      {
        protocol: "http",
        hostname: "162.215.10.70",
        port: "3515",
        pathname: "/uploads/**",
      },
      {
        protocol: "https",
        hostname: "apifranchise.mindconsulting.com.br",
        pathname: "/uploads/**",
      },
    ],
    dangerouslyAllowSVG: true,
    contentDispositionType: "attachment",
    formats: ["image/webp", "image/avif"],
  },

  // Performance optimizations
  experimental: {
    optimizePackageImports: [
      "@tanstack/react-query",
      "date-fns",
      "sonner",
      "zod",
    ],
  },

  async rewrites() {
    const internalUrl = process.env.API_INTERNAL_URL || 'http://host.docker.internal:4000'
    return {
      beforeFiles: [
        {
          source: '/uploads/:path*',
          destination: `${internalUrl}/uploads/:path*`,
        },
      ],
      afterFiles: [],
      fallback: [],
    }
  },

  // Headers for caching and compression
  async headers() {
    return [
      {
        source: "/fonts/(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
};

module.exports = withBundleAnalyzer(nextConfig);
