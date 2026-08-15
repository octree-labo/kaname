"use client";

import { useEffect, useRef, useState } from "react";

export interface SearchOption {
  id: number;
  label: string;
}

export function SearchSelect({
  id,
  value,
  onChange,
  fetchOptions,
  fetchLabel,
  placeholder,
  required,
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  fetchOptions: (keyword: string) => Promise<SearchOption[]>;
  fetchLabel: (id: number) => Promise<string | null>;
  placeholder?: string;
  required?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState("");
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<SearchOption[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!value) return;
    let cancelled = false;
    fetchLabel(Number(value)).then((l) => {
      if (!cancelled) setLabel(l ?? `#${value}`);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      fetchOptions(query).then((opts) => {
        if (!cancelled) setOptions(opts);
      });
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, open]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <input
        id={id}
        required={required && !value}
        value={open ? query : value ? label : ""}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          setQuery("");
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full pr-6"
      />
      {value && !open && (
        <button
          type="button"
          onClick={() => {
            onChange("");
            setLabel("");
          }}
          aria-label="選択をクリア"
          className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-700"
        >
          ×
        </button>
      )}
      {open && (
        <div className="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-slate-300 bg-white shadow-lg">
          {options.length === 0 && <div className="px-3 py-2 text-sm text-slate-600">該当なし</div>}
          {options.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => {
                onChange(String(opt.id));
                setLabel(opt.label);
                setOpen(false);
              }}
              className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-100"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
