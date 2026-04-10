"use client";

import type { TrendingEntity, TrendDirection, EntityType } from "@/lib/types";

const DIRECTION_STYLES: Record<
  TrendDirection,
  { label: string; classes: string; arrow: string }
> = {
  rising: {
    label: "Rising",
    arrow: "↑",
    classes: "bg-green-500/10 text-green-400 border border-green-500/20",
  },
  peak: {
    label: "Peak",
    arrow: "→",
    classes: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  },
  fading: {
    label: "Fading",
    arrow: "↓",
    classes: "bg-rose-500/10 text-rose-400 border border-rose-500/20",
  },
  new: {
    label: "New",
    arrow: "★",
    classes: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  },
};

const ENTITY_TYPE_LABEL: Record<EntityType, string> = {
  venue: "Venue",
  artist: "Artist",
  event: "Event",
  dish: "Dish",
};

function ScoreBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70
      ? "bg-green-500"
      : pct >= 45
      ? "bg-amber-500"
      : "bg-rose-500";

  return (
    <div className="flex items-center gap-2 mt-3">
      <div className="flex-1 h-1 rounded-full bg-zinc-800">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-zinc-500 tabular-nums w-8 text-right">
        {pct}
      </span>
    </div>
  );
}

export function TrendCard({ entity }: { entity: TrendingEntity }) {
  const dir = DIRECTION_STYLES[entity.trend_direction] ?? DIRECTION_STYLES.peak;
  const typeLabel = ENTITY_TYPE_LABEL[entity.entity_type] ?? entity.entity_type;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-white truncate leading-snug">
            {entity.entity_name}
          </p>
          <p className="text-xs text-zinc-500 mt-0.5">{typeLabel}</p>
        </div>
        <span
          className={`shrink-0 inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${dir.classes}`}
        >
          <span>{dir.arrow}</span>
          {dir.label}
        </span>
      </div>
      <ScoreBar value={entity.composite_score} />
    </div>
  );
}
