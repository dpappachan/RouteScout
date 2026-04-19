// Day-color palette used consistently across the map polylines, elevation
// chart day boundaries, and itinerary day bullets. Muted so they read well
// over the topo map tiles.

export const DAY_COLORS = [
  "#dc2626", // red-600
  "#2563eb", // blue-600
  "#16a34a", // green-600
  "#9333ea", // purple-600
  "#ea580c", // orange-600
  "#0891b2", // cyan-600
  "#db2777", // pink-600
];

export const CATEGORY_LABELS: Record<string, string> = {
  peak: "Peak",
  pass: "Pass",
  lake: "Lake",
  waterfall: "Waterfall",
  viewpoint: "Viewpoint",
  meadow: "Meadow",
};
