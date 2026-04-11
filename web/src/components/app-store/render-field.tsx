"use client";

import { Input } from "@/components/ui/input";
import type { FormField } from "@/data/types";

interface RenderFieldProps {
  field: FormField;
  value: string;
  onChange: (value: string) => void;
}

export function RenderField({ field, value, onChange }: RenderFieldProps) {
  const inputType = field.type === "password" ? "password" : field.type === "url" ? "url" : "text";

  return (
    <div>
      <label className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-[var(--text-muted)] uppercase tracking-wider block mb-1.5">
        {field.display_name}
        {field.required && <span className="text-[var(--rose)] ml-1">*</span>}
      </label>
      <Input
        type={inputType}
        placeholder={field.placeholder || ""}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-[var(--surface)] border-[var(--border)] text-[var(--text)] font-[family-name:var(--font-jetbrains-mono)] text-sm placeholder:text-[var(--text-muted)]"
      />
    </div>
  );
}
