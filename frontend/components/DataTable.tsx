"use client";

import Link from "next/link";

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => React.ReactNode;
  align?: "left" | "right";
}

export function DataTable<T extends { id: number }>({
  columns,
  rows,
  rowHref,
  emptyMessage = "データがありません",
}: {
  columns: Column<T>[];
  rows: T[];
  rowHref?: (row: T) => string;
  emptyMessage?: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-600">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-2 ${col.align === "right" ? "text-right" : "text-left"}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const cells = columns.map((col) => (
              <td
                key={col.key}
                className={`px-4 py-2 ${col.align === "right" ? "text-right" : "text-left"}`}
              >
                {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? "-")}
              </td>
            ));
            return (
              <tr key={row.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                {rowHref ? (
                  <>
                    {columns.map((col, i) => (
                      <td
                        key={col.key}
                        className={`px-4 py-2 ${col.align === "right" ? "text-right" : "text-left"}`}
                      >
                        {i === 0 ? (
                          <Link href={rowHref(row)} className="text-slate-900 hover:underline">
                            {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? "-")}
                          </Link>
                        ) : col.render ? (
                          col.render(row)
                        ) : (
                          String((row as Record<string, unknown>)[col.key] ?? "-")
                        )}
                      </td>
                    ))}
                  </>
                ) : (
                  cells
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
