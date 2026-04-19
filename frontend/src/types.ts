// Mirrors backend/api/models.py — keep in sync when the API schema changes.

export type FeatureCategory =
  | "peak"
  | "lake"
  | "waterfall"
  | "meadow"
  | "pass"
  | "viewpoint";

export interface FeatureInfo {
  name: string;
  category: FeatureCategory;
  lat: number;
  lon: number;
}

export interface DayPlan {
  day: number;
  length_miles: number;
  gain_m: number;
  camp_name: string;
  camp_lat: number;
  camp_lon: number;
  path_coords: [number, number][]; // [lat, lon]
  path_elevations_m: number[];
  path_cumulative_miles: number[];
  features_passed: FeatureInfo[];
}

export interface ParsedSpec {
  days: number;
  miles_per_day: number;
  start: string;
  end: string | null;
  preferred_categories: string[];
  named_must_visit: string[];
  rationale: string;
}

export interface PlanResponse {
  prompt: string;
  parsed: ParsedSpec;
  total_length_miles: number;
  total_gain_m: number;
  score: number;
  days: DayPlan[];
  narrative: string;
  elapsed_seconds: { parse: number; plan: number; narrate: number };
}

export interface ApiError {
  error: string;
  detail?: string;
}
