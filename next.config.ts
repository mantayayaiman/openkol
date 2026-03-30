import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  allowedDevOrigins: ['ricky-currently-choice-gtk.trycloudflare.com', 'given-commented-cons-thermal.trycloudflare.com', 'circumstances-expenditure-monkey-kent.trycloudflare.com', 'gmc-consulting-trucks-boat.trycloudflare.com', 'dialogue-burner-felt-citations.trycloudflare.com', 'api.trycloudflare.com', 'waterproof-craps-sides-robin.trycloudflare.com', 'Binary file /tmp/cloudflare_tunnel.log matches', 'replica-ecommerce-reasonably-track.trycloudflare.com', 'whale-alexandria-completion-supreme.trycloudflare.com', 'trademarks-psychiatry-statement-puts.trycloudflare.com', 'gain-parties-stock-macintosh.trycloudflare.com', 'futures-adventures-folks-conversations.trycloudflare.com', 'schemes-bicycle-floral-inclusive.trycloudflare.com', 'saw-table-internal-governments.trycloudflare.com', 'organ-java-grip-settled.trycloudflare.com'],
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
