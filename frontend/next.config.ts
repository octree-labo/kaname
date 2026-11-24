import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 紹介用 LP（public/lp/index.html）を /lp で返す。ログインもゲストセッションも不要（proxy.ts の matcher で除外）
  async rewrites() {
    return [{ source: "/lp", destination: "/lp/index.html" }];
  },
};

export default nextConfig;
