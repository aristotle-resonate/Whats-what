"use client";

import { CATEGORIES, type Category } from "@/lib/types";

interface CategoryTabsProps {
  value: Category;
  onChange: (cat: Category) => void;
}

export function CategoryTabs({ value, onChange }: CategoryTabsProps) {
  return (
    <div className="flex border-b border-zinc-800">
      {CATEGORIES.map((cat) => (
        <button
          key={cat.slug}
          onClick={() => onChange(cat.slug)}
          className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-xs font-medium transition-colors border-b-2 -mb-px ${
            value === cat.slug
              ? "border-white text-white"
              : "border-transparent text-zinc-500 hover:text-zinc-300"
          }`}
        >
          <span className="text-base leading-none">{cat.emoji}</span>
          {cat.label}
        </button>
      ))}
    </div>
  );
}
