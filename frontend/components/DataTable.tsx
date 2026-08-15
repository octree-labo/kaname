"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => React.ReactNode;
  align?: "left" | "right";
  sortable?: boolean;
  /** ソート時に比較する値。省略時は row[key] を使う。 */
  sortValue?: (row: T) => string | number | null | undefined;
}

export function DataTable<T extends { id: number }>({
  columns,
  rows,
  rowHref,
  emptyMessage = "データがありません",
  maxHeight = "100%",
}: {
  columns: Column<T>[];
  rows: T[];
  rowHref?: (row: T) => string;
  emptyMessage?: string;
  maxHeight?: string;
}) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return rows;
    const accessor =
      col.sortValue ?? ((row: T) => (row as unknown as Record<string, unknown>)[sortKey] as string | number | null | undefined);
    const withIndex = rows.map((row, index) => ({ row, index }));
    withIndex.sort((a, b) => {
      const av = accessor(a.row);
      const bv = accessor(b.row);
      if (av == null && bv == null) return a.index - b.index;
      if (av == null) return 1;
      if (bv == null) return -1;
      let cmp: number;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv), "ja");
      }
      if (cmp === 0) cmp = a.index - b.index;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return withIndex.map((w) => w.row);
  }, [rows, sortKey, sortDir, columns]);

  function handleHeaderClick(col: Column<T>) {
    if (!col.sortable) return;
    if (sortKey === col.key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col.key);
      setSortDir("asc");
    }
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-slate-200 bg-white">
      <div className="min-h-0 flex-1 overflow-auto" style={{ maxHeight }}>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-600">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleHeaderClick(col)}
                  className={`bg-slate-50 px-4 py-2 ${col.align === "right" ? "text-right" : "text-left"} ${
                    col.sortable ? "cursor-pointer select-none hover:text-slate-900" : ""
                  }`}
                >
                  {col.label}
                  {col.sortable && sortKey === col.key && (sortDir === "asc" ? " ▲" : " ▼")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={row.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                {columns.map((col, i) => {
                  const content = col.render
                    ? col.render(row)
                    : String((row as Record<string, unknown>)[col.key] ?? "-");
                  return (
                    <td key={col.key} className={`px-4 py-2 ${col.align === "right" ? "text-right" : "text-left"}`}>
                      {rowHref && i === 0 ? (
                        <Link href={rowHref(row)} className="text-slate-900 hover:underline">
                          {content}
                        </Link>
                      ) : (
                        content
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
