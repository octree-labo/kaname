export function formatNumber(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("ja-JP");
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return value;
}

const APPROVAL_STATUS_LABEL: Record<string, string> = {
  draft: "未承認",
  pending: "承認待ち",
  approved: "承認済み",
  rejected: "却下",
};

const DOCUMENT_STATUS_LABEL: Record<string, string> = {
  draft: "下書き",
  confirmed: "確定",
  cancelled: "取消",
};

export function formatApprovalStatus(status: string): string {
  return APPROVAL_STATUS_LABEL[status] ?? status;
}

export function formatDocumentStatus(status: string): string {
  return DOCUMENT_STATUS_LABEL[status] ?? status;
}

export const ROUNDING_TYPE_LABEL: Record<string, string> = {
  floor: "切り捨て",
  ceil: "切り上げ",
  round: "四捨五入",
};

export function formatRoundingType(value: string): string {
  return ROUNDING_TYPE_LABEL[value] ?? value;
}
