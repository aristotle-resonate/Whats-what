"use client";

import { CITIES } from "@/lib/types";

interface CitySelectorProps {
  value: string;
  onChange: (city: string) => void;
}

export function CitySelector({ value, onChange }: CitySelectorProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
      {CITIES.map((city) => (
        <button
          key={city.slug}
          onClick={() => onChange(city.slug)}
          className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            value === city.slug
              ? "bg-white text-zinc-950"
              : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
          }`}
        >
          {city.label}
        </button>
      ))}
    </div>
  );
}
