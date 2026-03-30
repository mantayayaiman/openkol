import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  allowedDevOrigins: ['whale-alexandria-completion-supreme.trycloudflare.com', 'trademarks-psychiatry-statement-puts.trycloudflare.com', 'gain-parties-stock-macintosh.trycloudflare.com', 'futures-adventures-folks-conversations.trycloudflare.com', 'schemes-bicycle-floral-inclusive.trycloudflare.com', 'saw-table-internal-governments.trycloudflare.com', 'organ-java-grip-settled.trycloudflare.com'],
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'api.dicebear.com' },
      { protocol: 'https', hostname: '*.tiktokcdn.com' },
      { protocol: 'https', hostname: '*.cdninstagram.com' },
      { protocol: 'https', hostname: '*.ggpht.com' },
      { protocol: 'https', hostname: '*.googleusercontent.com' },
    ],
  },
};

export default nextConfig;
