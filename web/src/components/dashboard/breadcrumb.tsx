"use client";

import Link from "next/link";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="flex items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-[var(--text-muted)] mb-6">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <span className="text-[var(--text-muted)]">/</span>}
          {item.href ? (
            <Link
              href={item.href}
              className="text-[var(--text-dim)] no-underline hover:text-[var(--accent)] transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-[var(--text)]">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
