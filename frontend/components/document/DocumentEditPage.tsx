"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { DocumentModuleConfig } from "@/lib/documentModules";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductLineFields } from "@/components/ProductLineFields";
import { buildProductLinePayload, type ProductLineValue } from "@/lib/lineHelpers";

interface DocLine {
  id: number;
  productId?: number;
  quantity?: string | null;
  unitPrice?: string | null;
  amount: string;
}

interface DocDetail {
  id: number;
  partnerId: number;
  status?: string;
  lines: DocLine[];
  [key: string]: unknown;
}

interface ProductLineEdit extends ProductLineValue {
  id: number;
}

interface AmountLineEdit {
  id: number;
  amount: string;
}

export function DocumentEditPage({ config }: { config: DocumentModuleConfig }) {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data } = useSWR<DocDetail>(`${config.apiPath}/${params.id}`, fetcher);

  const [partnerId, setPartnerId] = useState("");
  const [date, setDate] = useState("");
  const [status, setStatus] = useState("");
  const [productLines, setProductLines] = useState<ProductLineEdit[]>([]);
  const [amountLines, setAmountLines] = useState<AmountLineEdit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!data) return;
    // SWRで取得した既存データを編集用の下書きstateへ一度だけ複製する
    // （その後はユーザーの入力でstateが独立に変化するため、派生値としては計算できない）。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPartnerId(String(data.partnerId));
    setDate(String(data[config.dateField] ?? ""));
    setStatus(String(data.status ?? ""));
    if (config.lineKind === "product") {
      setProductLines(
        data.lines.map((l) => ({
          id: l.id,
          productId: String(l.productId ?? ""),
          quantity: l.quantity ?? "",
          unitPrice: l.unitPrice ?? "",
          amount: l.amount,
        }))
      );
    } else {
      setAmountLines(data.lines.map((l) => ({ id: l.id, amount: l.amount })));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (!data) return <p className="text-sm text-slate-600">読み込み中...</p>;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const lines =
        config.lineKind === "product"
          ? productLines.map((l) => ({ id: l.id, ...buildProductLinePayload(l) }))
          : amountLines.map((l) => ({ id: l.id, amount: Number(l.amount) }));

      const body: Record<string, unknown> = {
        partnerId: Number(partnerId),
        [config.dateField]: date,
        lines,
      };
      if (config.hasStatus) body.status = status;

      await api.patch(`${config.apiPath}/${params.id}`, body);
      router.push(`/${config.key}/${params.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "更新に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">{config.label} 編集</h1>
      <p className="mt-1 text-xs text-slate-600">
        既存明細の商品・数量・単価（または金額）のみ変更できます。明細の追加・削除には対応していません。
        数量・単価を両方入力すると金額は取引先の丸め区分で自動計算されます。
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="editPartnerId" className="block text-sm font-medium text-slate-700">取引先</label>
            <div className="mt-1">
              <PartnerPicker id="editPartnerId" value={partnerId} onChange={setPartnerId} required />
            </div>
          </div>
          <div>
            <label htmlFor="editDate" className="block text-sm font-medium text-slate-700">{config.dateLabel}</label>
            <input id="editDate" type="date" required value={date} onChange={(e) => setDate(e.target.value)} className="mt-1 w-full" />
          </div>
          {config.hasStatus && (
            <div>
              <label htmlFor="editStatus" className="block text-sm font-medium text-slate-700">状態</label>
              <select id="editStatus" value={status} onChange={(e) => setStatus(e.target.value)} className="mt-1 w-full">
                <option value="draft">下書き</option>
                <option value="confirmed">確定</option>
                <option value="cancelled">取消</option>
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">明細</label>
          <div className="mt-2 space-y-2">
            {config.lineKind === "product"
              ? productLines.map((line, i) => (
                  <div key={line.id} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                    <ProductLineFields
                      value={line}
                      onChange={(next) =>
                        setProductLines((prev) => prev.map((l, idx) => (idx === i ? { ...next, id: l.id } : l)))
                      }
                    />
                  </div>
                ))
              : amountLines.map((line, i) => (
                  <div key={line.id} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                    <div className="w-40">
                      <label className="block text-xs text-slate-600">金額</label>
                      <input
                        required
                        type="number"
                        step="0.01"
                        value={line.amount}
                        onChange={(e) =>
                          setAmountLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, amount: e.target.value } : l)))
                        }
                        className="mt-1 w-full"
                      />
                    </div>
                  </div>
                ))}
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            保存
          </button>
          <button
            type="button"
            onClick={() => router.push(`/${config.key}/${params.id}`)}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
