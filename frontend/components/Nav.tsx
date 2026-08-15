"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

const NAV_GROUPS: { label: string; items: { href: string; label: string }[] }[] = [
  {
    label: "共通マスタ / 顧客管理",
    items: [
      { href: "/partners", label: "取引先" },
      { href: "/products", label: "商品" },
      { href: "/price-master", label: "単価" },
    ],
  },
  {
    label: "販売管理",
    items: [
      { href: "/quotations", label: "見積" },
      { href: "/orders", label: "受注" },
      { href: "/purchase-orders", label: "発注" },
      { href: "/purchases", label: "仕入" },
      { href: "/sales", label: "売上" },
      { href: "/receipts", label: "入金" },
      { href: "/payments", label: "支払" },
    ],
  },
  {
    label: "在庫",
    items: [{ href: "/inventory", label: "在庫・引当" }],
  },
];

export function Nav() {
  const pathname = usePathname();
  const { data: user } = useSWR<CurrentUser>("/auth/me", fetcher, { shouldRetryOnError: false });

  const groups = [...NAV_GROUPS];
  if (user?.role === "owner") {
    groups.push({ label: "オーナー", items: [{ href: "/owner", label: "オーナーメニュー" }] });
  }

  return (
    <nav className="flex h-full w-56 shrink-0 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white px-4 py-6">
      <Link href="/" className="px-2 text-sm font-semibold text-slate-900">
        基幹業務システム
      </Link>
      {groups.map((group) => (
        <div key={group.label}>
          <p className="px-2 text-xs font-medium uppercase tracking-wide text-slate-600">
            {group.label}
          </p>
          <ul className="mt-2 space-y-0.5">
            {group.items.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`block rounded-md px-2 py-1.5 text-sm ${
                      active
                        ? "bg-slate-900 text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
