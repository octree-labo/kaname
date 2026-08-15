"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { PartnerOut, PartnerType } from "@/lib/types";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewPartnerPage() {
  const router = useRouter();
  const [partnerCode, setPartnerCode] = useState("");
  const [partnerType, setPartnerType] = useState<PartnerType>("customer");
  const [name, setName] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(today());
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [representativeName, setRepresentativeName] = useState("");
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.post<PartnerOut>("/api/partners", {
        partnerCode: partnerCode || undefined,
        partnerType,
        detail: {
          effectiveDate,
          name,
          address: address || undefined,
          phone: phone || undefined,
          representativeName: representativeName || undefined,
          remarks: remarks || undefined,
        },
      });
      router.push(`/partners/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登録に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-semibold text-slate-900">取引先 新規登録</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="partnerCode" className="block text-sm font-medium text-slate-700">取引先コード</label>
          <input
            id="partnerCode"
            value={partnerCode}
            onChange={(e) => setPartnerCode(e.target.value)}
            placeholder="空欄で自動採番（000001〜）"
            className="mt-1 w-full"
          />
        </div>

        <div>
          <label htmlFor="partnerType" className="block text-sm font-medium text-slate-700">区分</label>
          <select
            id="partnerType"
            value={partnerType}
            onChange={(e) => setPartnerType(e.target.value as PartnerType)}
            className="mt-1 w-full"
          >
            <option value="customer">得意先</option>
            <option value="supplier">仕入先</option>
            <option value="both">得意先/仕入先</option>
          </select>
        </div>

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-slate-700">会社名</label>
          <input id="name" required value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full" />
        </div>

        <div>
          <label htmlFor="representativeName" className="block text-sm font-medium text-slate-700">代表者名</label>
          <input
            id="representativeName"
            value={representativeName}
            onChange={(e) => setRepresentativeName(e.target.value)}
            className="mt-1 w-full"
          />
        </div>

        <div>
          <label htmlFor="address" className="block text-sm font-medium text-slate-700">住所</label>
          <input id="address" value={address} onChange={(e) => setAddress(e.target.value)} className="mt-1 w-full" />
        </div>

        <div>
          <label htmlFor="phone" className="block text-sm font-medium text-slate-700">電話番号</label>
          <input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} className="mt-1 w-full" />
        </div>

        <div>
          <label htmlFor="remarks" className="block text-sm font-medium text-slate-700">特記事項（手入力）</label>
          <textarea id="remarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} className="mt-1 w-full" rows={3} />
        </div>

        <div>
          <label htmlFor="effectiveDate" className="block text-sm font-medium text-slate-700">情報の反映日</label>
          <input
            id="effectiveDate"
            type="date"
            required
            value={effectiveDate}
            onChange={(e) => setEffectiveDate(e.target.value)}
            className="mt-1 w-full"
          />
          <p className="mt-1 text-xs text-slate-600">
            本日日付＝即時反映。未来日付を指定すると、その日付を境に自動的に反映されます。
          </p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          登録
        </button>
      </form>
    </div>
  );
}
