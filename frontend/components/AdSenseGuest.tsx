"use client";

import Script from "next/script";
import { useCurrentUser } from "@/lib/useCurrentUser";

/** ゲスト(未ログイン)閲覧時のみAdSense広告スクリプトを読み込む。 */
export function AdSenseGuest() {
  const { isGuest } = useCurrentUser();

  if (!isGuest) return null;

  return (
    <Script
      async
      src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8597842934542691"
      crossOrigin="anonymous"
      strategy="afterInteractive"
    />
  );
}
