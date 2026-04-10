"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

import { CitySelector } from "@/components/CitySelector";
import { CategoryTabs } from "@/components/CategoryTabs";
import { TrendCard } from "@/components/TrendCard";
import { fetchTrending } from "@/lib/api";
import type { TrendingEntity, Category } from "@/lib/types";

export default function Home() {
  const [city, setCity] = useState("austin");
  const [category, setCategory] = useState<Category>("music");
  const [entities, setEntities] = useState<TrendingEntity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTrending(city, category);
      setEntities(data.entities);
    } catch {
      setError("Couldn't load trending data — is the backend running?");
      setEntities([]);
    } finally {
      setLoading(false);
    }
  }, [city, category]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-zinc-950/90 backdrop-blur border-b border-zinc-800/60 px-4 pt-4 pb-3 space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold tracking-tight">Whats-What</h1>
          <Link
            href="/auth/sign-in"
            className="text-xs text-zinc-400 hover:text-white transition-colors"
          >
            Sign in
          </Link>
        </div>
        <CitySelector value={city} onChange={setCity} />
        <CategoryTabs value={category} onChange={setCategory} />
      </header>

      {/* Feed */}
      <section className="px-4 py-4 space-y-3 max-w-lg mx-auto">
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-20 rounded-xl bg-zinc-900 animate-pulse"
              />
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="text-center py-16">
            <p className="text-zinc-500 text-sm">{error}</p>
            <button
              onClick={load}
              className="mt-3 text-xs text-zinc-400 underline"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && entities.length === 0 && (
          <div className="text-center py-16">
            <p className="text-zinc-500 text-sm">
              No data yet — check back after the first collection run.
            </p>
          </div>
        )}

        {!loading &&
          entities.map((entity, i) => (
            <TrendCard key={`${entity.entity_name}-${i}`} entity={entity} />
          ))}
      </section>
    </main>
  );
}
