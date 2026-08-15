"use client";

import { api } from "@/lib/api";
import type { PartnerWithCurrentDetailOut } from "@/lib/types";
import { SearchSelect } from "@/components/SearchSelect";

function partnerLabel(p: PartnerWithCurrentDetailOut): string {
  return `${p.partnerCode} ${p.currentDetail?.name ?? ""}`.trim();
}

export function PartnerPicker({
  id,
  value,
  onChange,
  placeholder = "コード・会社名で検索",
  required,
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <SearchSelect
      id={id}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      fetchOptions={async (keyword) => {
        const list = await api.get<PartnerWithCurrentDetailOut[]>(
          `/api/partners?keyword=${encodeURIComponent(keyword)}&page_size=20`
        );
        return list.map((p) => ({ id: p.id, label: partnerLabel(p) }));
      }}
      fetchLabel={async (partnerId) => {
        try {
          const p = await api.get<PartnerWithCurrentDetailOut>(`/api/partners/${partnerId}`);
          return partnerLabel(p);
        } catch {
          return null;
        }
      }}
    />
  );
}
