export type TrendDirection = "rising" | "peak" | "fading" | "new";
export type EntityType = "venue" | "artist" | "event" | "dish";
export type Category = "music" | "food" | "fitness" | "networking";

export interface TrendingEntity {
  entity_name: string;
  entity_type: EntityType;
  category: Category;
  composite_score: number;
  volume_score: number;
  sentiment_score: number;
  freshness_score: number;
  trend_direction: TrendDirection;
  scored_at: string;
}

export interface TrendingResponse {
  city: string;
  category: string | null;
  entities: TrendingEntity[];
}

export const CITIES: { slug: string; label: string }[] = [
  { slug: "austin", label: "Austin, TX" },
  { slug: "dallas", label: "Dallas, TX" },
  { slug: "san-antonio", label: "San Antonio, TX" },
  { slug: "new-york", label: "New York, NY" },
  { slug: "los-angeles", label: "Los Angeles, CA" },
];

export const CATEGORIES: { slug: Category; label: string; emoji: string }[] = [
  { slug: "music", label: "Music", emoji: "🎵" },
  { slug: "food", label: "Food", emoji: "🍽" },
  { slug: "fitness", label: "Fitness", emoji: "💪" },
  { slug: "networking", label: "Networking", emoji: "🤝" },
];
