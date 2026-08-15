"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type {
  PartnerDetailOut,
  PartnerType,
  PartnerWithCurrentDetailOut,
  RoundingType,
  TransactionHistoryResponse,
} from "@/lib/types";
import { formatNumber, formatRoundingType } from "@/lib/format";

const PARTNER_TYPE_LABEL: Record<string, string> = {
  customer: "得意先",
  supplier: "仕入先",
  both: "得意先/仕入先",
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const TRANSACTION_TYPE_LABEL: Record<string, string> = {
  quotation: "見積",
  order: "受注",
  purchase_order: "発注",
  purchase: "仕入",
  sales: "売上",
  receipt: "入金",
  payment: "支払",
};

export default function PartnerDetailPage() {
  const params = useParams<{ id: string }>();
  const partnerId = params.id;

  const { data: partner, mutate: mutatePartner } = useSWR<PartnerWithCurrentDetailOut>(
    `/api/partners/${partnerId}`,
    fetcher
  );
  const { data: details, mutate: mutateDetails } = useSWR<PartnerDetailOut[]>(
    `/api/partners/${partnerId}/details`,
    fetcher
  );
  const { data: transactions } = useSWR<TransactionHistoryResponse>(
    `/api/partners/${partnerId}/transactions`,
    fetcher
  );

  const [showForm, setShowForm] = useState(false);
  const [effectiveDate, setEffectiveDate] = useState(today());
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [representativeName, setRepresentativeName] = useState("");
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [showSettings, setShowSettings] = useState(false);
  const [settingsPartnerType, setSettingsPartnerType] = useState<PartnerType>("customer");
  const [settingsRoundingType, setSettingsRoundingType] = useState<RoundingType>("round");
  const [settingsIsActive, setSettingsIsActive] = useState(true);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [settingsSubmitting, setSettingsSubmitting] = useState(false);

  if (!partner) return <p className="text-sm text-slate-600">読み込み中...</p>;
  const current = partner.currentDetail;

  function openSettings() {
    setSettingsPartnerType(partner!.partnerType);
    setSettingsRoundingType(partner!.roundingType);
    setSettingsIsActive(partner!.isActive);
    setShowSettings(true);
  }

  async function handleSettingsSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSettingsError(null);
    setSettingsSubmitting(true);
    try {
      await api.patch(`/api/partners/${partnerId}`, {
        partnerType: settingsPartnerType,
        roundingType: settingsRoundingType,
        isActive: settingsIsActive,
      });
      setShowSettings(false);
      mutatePartner();
    } catch (err) {
      setSettingsError(err instanceof ApiError ? err.message : "更新に失敗しました");
    } finally {
      setSettingsSubmitting(false);
    }
  }

  function openForm() {
    setName(current?.name ?? "");
    setAddress(current?.address ?? "");
    setPhone(current?.phone ?? "");
    setRepresentativeName(current?.representativeName ?? "");
    setRemarks("");
    setEffectiveDate(today());
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post(`/api/partners/${partnerId}/details`, {
        effectiveDate,
        name,
        address: address || undefined,
        phone: phone || undefined,
        representativeName: representativeName || undefined,
        remarks: remarks || undefined,
      });
      setShowForm(false);
      mutatePartner();
      mutateDetails();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "更新に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">
          {current?.name ?? "(未設定)"}
          <span className="ml-2 text-sm font-normal text-slate-600">{partner.partnerCode}</span>
        </h1>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">設定</h2>
          <button
            onClick={openSettings}
            className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
          >
            設定を変更
          </button>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-slate-600">区分</dt>
          <dd>{PARTNER_TYPE_LABEL[partner.partnerType]}</dd>
          <dt className="text-slate-600">金額端数処理</dt>
          <dd>{formatRoundingType(partner.roundingType)}</dd>
          <dt className="text-slate-600">状態</dt>
          <dd>{partner.isActive ? "有効" : "無効"}</dd>
        </dl>

        {showSettings && (
          <form onSubmit={handleSettingsSubmit} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <div>
              <label htmlFor="settingsPartnerType" className="block text-sm font-medium text-slate-700">区分</label>
              <select
                id="settingsPartnerType"
                value={settingsPartnerType}
                onChange={(e) => setSettingsPartnerType(e.target.value as PartnerType)}
                className="mt-1 w-full"
              >
                <option value="customer">得意先</option>
                <option value="supplier">仕入先</option>
                <option value="both">得意先/仕入先</option>
              </select>
            </div>
            <div>
              <label htmlFor="settingsRoundingType" className="block text-sm font-medium text-slate-700">金額端数処理</label>
              <select
                id="settingsRoundingType"
                value={settingsRoundingType}
                onChange={(e) => setSettingsRoundingType(e.target.value as RoundingType)}
                className="mt-1 w-full"
              >
                <option value="round">四捨五入</option>
                <option value="floor">切り捨て</option>
                <option value="ceil">切り上げ</option>
              </select>
              <p className="mt-1 text-xs text-slate-600">
                変更後に新しく作成する伝票明細から適用されます。既存の明細は作成時点の端数処理方法を保持します。
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="settingsIsActive"
                type="checkbox"
                checked={settingsIsActive}
                onChange={(e) => setSettingsIsActive(e.target.checked)}
              />
              <label htmlFor="settingsIsActive" className="text-sm text-slate-700">有効</label>
            </div>
            {settingsError && <p className="text-sm text-red-600">{settingsError}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={settingsSubmitting}
                className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
              >
                保存
              </button>
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
              >
                キャンセル
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">現在の情報</h2>
          <button
            onClick={openForm}
            className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
          >
            情報を変更
          </button>
        </div>
        {current ? (
          <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <dt className="text-slate-600">会社名</dt>
            <dd>{current.name}</dd>
            <dt className="text-slate-600">代表者</dt>
            <dd>{current.representativeName ?? "-"}</dd>
            <dt className="text-slate-600">住所</dt>
            <dd>{current.address ?? "-"}</dd>
            <dt className="text-slate-600">電話番号</dt>
            <dd>{current.phone ?? "-"}</dd>
            <dt className="text-slate-600">適用開始日</dt>
            <dd>{current.effectiveDate}</dd>
          </dl>
        ) : (
          <p className="mt-3 text-sm text-slate-600">現在有効な情報がありません。</p>
        )}

        {showForm && (
          <form onSubmit={handleSubmit} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <div>
              <label htmlFor="editEffectiveDate" className="block text-sm font-medium text-slate-700">反映日</label>
              <input
                id="editEffectiveDate"
                type="date"
                required
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                className="mt-1 w-48"
              />
              <p className="mt-1 text-xs text-slate-600">
                本日日付＝即時反映。将来日付を指定すると、その日を境に自動的に切り替わります（例：来月の社長交代）。過去日付なら遡及訂正にも使えます。
              </p>
            </div>
            <div>
              <label htmlFor="editName" className="block text-sm font-medium text-slate-700">会社名</label>
              <input id="editName" required value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full" />
            </div>
            <div>
              <label htmlFor="editRepresentativeName" className="block text-sm font-medium text-slate-700">代表者名</label>
              <input
                id="editRepresentativeName"
                value={representativeName}
                onChange={(e) => setRepresentativeName(e.target.value)}
                className="mt-1 w-full"
              />
            </div>
            <div>
              <label htmlFor="editAddress" className="block text-sm font-medium text-slate-700">住所</label>
              <input id="editAddress" value={address} onChange={(e) => setAddress(e.target.value)} className="mt-1 w-full" />
            </div>
            <div>
              <label htmlFor="editPhone" className="block text-sm font-medium text-slate-700">電話番号</label>
              <input id="editPhone" value={phone} onChange={(e) => setPhone(e.target.value)} className="mt-1 w-full" />
            </div>
            <div>
              <label htmlFor="editRemarks" className="block text-sm font-medium text-slate-700">特記事項（手入力）</label>
              <textarea id="editRemarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} className="mt-1 w-full" rows={2} />
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
                onClick={() => setShowForm(false)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
              >
                キャンセル
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">変更履歴</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">適用開始日</th>
                <th className="px-3 py-2">会社名</th>
                <th className="px-3 py-2">代表者</th>
                <th className="px-3 py-2">住所</th>
                <th className="px-3 py-2">特記事項</th>
                <th className="px-3 py-2">登録日時</th>
              </tr>
            </thead>
            <tbody>
              {(details ?? []).map((d) => (
                <tr key={d.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{d.effectiveDate}</td>
                  <td className="px-3 py-2">{d.name}</td>
                  <td className="px-3 py-2">{d.representativeName ?? "-"}</td>
                  <td className="px-3 py-2">{d.address ?? "-"}</td>
                  <td className="px-3 py-2">{d.remarks ?? "-"}</td>
                  <td className="px-3 py-2 text-slate-600">{d.createdAt.slice(0, 16).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">取引履歴</h2>
        <p className="mt-1 text-xs text-slate-600">見積/受注/発注/仕入/売上/入金/支払の横断参照</p>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">種別</th>
                <th className="px-3 py-2">伝票番号</th>
                <th className="px-3 py-2">日付</th>
                <th className="px-3 py-2 text-right">金額</th>
                <th className="px-3 py-2">状態</th>
              </tr>
            </thead>
            <tbody>
              {(transactions?.data ?? []).map((t) => (
                <tr key={`${t.type}-${t.documentNo}`} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{TRANSACTION_TYPE_LABEL[t.type] ?? t.type}</td>
                  <td className="px-3 py-2">{t.documentNo}</td>
                  <td className="px-3 py-2">{t.documentDate}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(t.amount)}</td>
                  <td className="px-3 py-2">{t.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
