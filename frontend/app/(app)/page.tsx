import Link from "next/link";

const CARDS = [
  { href: "/partners", label: "取引先", desc: "共通マスタ・顧客管理" },
  { href: "/quotations", label: "見積", desc: "見積入力・承認・受注確定" },
  { href: "/orders", label: "受注", desc: "受注入力" },
  { href: "/purchase-orders", label: "発注", desc: "発注入力" },
  { href: "/purchases", label: "仕入", desc: "仕入入力" },
  { href: "/sales", label: "売上", desc: "売上入力" },
  { href: "/receipts", label: "入金", desc: "入金入力" },
  { href: "/payments", label: "支払", desc: "支払入力" },
  { href: "/inventory", label: "在庫・引当", desc: "在庫数・引当状況" },
];

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">ダッシュボード</h1>
      <p className="mt-1 text-sm text-slate-500">
        各業務モジュールへのショートカットです。
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400"
          >
            <p className="font-medium text-slate-900">{card.label}</p>
            <p className="mt-1 text-sm text-slate-500">{card.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
