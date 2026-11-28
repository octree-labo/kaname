import type { MetadataRoute } from "next"

// 公開しているのは /lp(紹介LP)と /privacy のみ。ダッシュボード等の
// アプリ本体はログイン/ゲストセッション前提のため対象外(robots.txt参照)。
export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://kaname.ajesta.work"
  return [
    { url: `${base}/lp`, lastModified: "2026-11-28" },
    { url: `${base}/privacy` },
  ]
}
