export const metadata = {
  title: "プライバシーポリシー | 基幹業務システム",
  description: "kaname.ajesta.work におけるCookie利用・広告配信・アクセス解析に関するプライバシーポリシー。",
};

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen justify-center px-4 py-16">
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">
          プライバシーポリシー
        </h1>

        <div className="mt-6 space-y-6 text-sm leading-relaxed text-slate-600">
          <section>
            <h2 className="text-sm font-medium text-slate-900">
              アクセス解析について
            </h2>
            <p className="mt-1">
              当サイトでは、Googleが提供するGoogle Analyticsを利用してアクセス状況を計測しています。
              Google Analyticsは、Cookieを使用してデータを収集しますが、氏名や住所などの個人を特定する情報は含まれません。
              この機能はCookieを無効にすることで収集を拒否することが可能です。詳細は
              <a
                href="https://marketingplatform.google.com/about/analytics/terms/jp/"
                className="text-slate-900 underline underline-offset-2"
                target="_blank"
                rel="noopener noreferrer"
              >
                Google Analytics利用規約
              </a>
              をご確認ください。
            </p>
          </section>

          <section>
            <h2 className="text-sm font-medium text-slate-900">
              広告配信について
            </h2>
            <p className="mt-1">
              当サイトでは、ゲスト（未ログイン・読み取り専用）閲覧時に限り、第三者配信の広告サービス（Google
              AdSense）を利用しています。ログインしてご利用いただく画面には広告は表示されません。広告配信事業者は、ユーザーの興味に応じた広告を表示するためにCookieを使用することがあります。Cookieを無効にする設定およびGoogle
              AdSenseに関する詳細は
              <a
                href="https://policies.google.com/technologies/ads?hl=ja"
                className="text-slate-900 underline underline-offset-2"
                target="_blank"
                rel="noopener noreferrer"
              >
                広告 – ポリシーと規約 – Google
              </a>
              をご確認ください。
            </p>
            <p className="mt-1">
              欧州経済領域（EEA）、英国、スイスからアクセスいただいた方には、Cookie利用に関する同意確認メッセージを表示し、選択いただいた内容に基づいて広告配信を行います。
            </p>
          </section>

          <section>
            <h2 className="text-sm font-medium text-slate-900">
              ゲスト閲覧について
            </h2>
            <p className="mt-1">
              本サービスはデモとして、認証なしで閲覧できるゲストモードを提供しています。ゲストモードでは新規作成・編集などの書き込み操作はできません。
            </p>
          </section>

          <section>
            <h2 className="text-sm font-medium text-slate-900">お問い合わせ</h2>
            <p className="mt-1">
              本ポリシーに関するお問い合わせは、運営者までご連絡ください。
            </p>
          </section>

          <p className="text-xs text-slate-400">最終更新日: 2026年8月</p>
        </div>

        <a
          href="/"
          className="mt-8 inline-block text-xs text-slate-500 underline underline-offset-2"
        >
          ← トップへもどる
        </a>
      </div>
    </div>
  );
}
