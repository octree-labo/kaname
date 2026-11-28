"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { DocumentModuleConfig } from "@/lib/documentModules";
import type { OpenLineOut } from "@/lib/types";
import { formatNumber } from "@/lib/format";

/**
 * 「上位伝票から取り込む」パネル。
 * 残（数量または金額）が残っている上位明細を一覧し、選んだ明細を下位伝票の明細として取り込む。
 * 明細IDを手で打ち込まなくても、伝票どうしをつなげられるようにするためのもの。
 */
export function UpstreamImport({
  config,
  partnerId,
  onImport,
}: {
  config: DocumentModuleConfig;
  partnerId: string;
  onImport: (lines: OpenLineOut[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  // 受注→発注は得意先と仕入先が別なので、取引先では絞り込まない
  const filterByPartner = config.openLinesKind !== "order_for_purchase" && partnerId !== "";
  const params = new URLSearchParams();
  if (filterByPartner) params.set("partner_id", partnerId);
  const key = open && config.openLinesKind ? `/api/open-lines/${config.openLinesKind}?${params.toString()}` : null;
  const { data, error, isLoading } = useSWR<OpenLineOut[]>(key, fetcher);

  if (!config.openLinesKind) return null;
  const isAmount = config.lineKind === "amount";
  const docLabel = config.upstreamDocLabel ?? "上位伝票";

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleImport() {
    const lines = (data ?? []).filter((l) => selected.has(l.lineId));
    if (lines.length === 0) return;
    onImport(lines);
    setSelected(new Set());
    setOpen(false);
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
      >
        {docLabel}から取り込む
      </button>
    );
  }

  return (
    <div className="mt-2 rounded-md border border-sky-200 bg-sky-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-slate-700">
          {isAmount ? "未" + (config.key === "receipts" ? "入金" : "払") + "の残っている" : "残数のある"}
          {docLabel}の明細です。
          {filterByPartner ? "選んだ取引先の分だけを表示しています。" : config.openLinesKind === "order_for_purchase" ? "" : "取引先を先に選ぶと絞り込めます。"}
        </p>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-slate-600 hover:underline">
          閉じる
        </button>
      </div>

      {isLoading && <p className="mt-2 text-xs text-slate-600">読み込み中…</p>}
      {error && <p className="mt-2 text-xs text-red-600">読み込みに失敗しました</p>}
      {data && data.length === 0 && <p className="mt-2 text-xs text-slate-600">取り込める明細はありません。</p>}

      {data && data.length > 0 && (
        <>
          <div className="mt-2 max-h-64 overflow-auto rounded border border-slate-200 bg-white">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-slate-100 text-slate-600">
                <tr>
                  <th className="px-2 py-1"></th>
                  <th className="px-2 py-1 text-left">{docLabel}番号</th>
                  <th className="px-2 py-1 text-left">日付</th>
                  {!filterByPartner && <th className="px-2 py-1 text-left">取引先</th>}
                  <th className="px-2 py-1 text-left">商品</th>
                  <th className="px-2 py-1 text-right">{isAmount ? "残額" : "残数"}</th>
                </tr>
              </thead>
              <tbody>
                {data.map((l) => (
                  <tr key={l.lineId} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-2 py-1 text-center">
                      <input
                        type="checkbox"
                        aria-label={`${l.documentNo} ${l.lineNo}行目を選ぶ`}
                        checked={selected.has(l.lineId)}
                        onChange={() => toggle(l.lineId)}
                      />
                    </td>
                    <td className="px-2 py-1">
                      {l.documentNo}-{l.lineNo}
                    </td>
                    <td className="px-2 py-1">{l.documentDate}</td>
                    {!filterByPartner && <td className="px-2 py-1">{l.partnerName ?? l.partnerId}</td>}
                    <td className="px-2 py-1">
                      {l.productCode} {l.productName}
                    </td>
                    <td className="px-2 py-1 text-right">
                      {formatNumber(isAmount ? l.remainingAmount : l.remainingQty)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={handleImport}
              disabled={selected.size === 0}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              選んだ {selected.size} 行を取り込む
            </button>
          </div>
        </>
      )}
    </div>
  );
}
