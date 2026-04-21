import L from "leaflet";
import { useEffect } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import { CATEGORY_LABELS, DAY_COLORS } from "../constants";
import type { FeatureCategory, PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
  selectedDay: number | null;
}

// SVG-based, recognizably-different marker shapes per role:
//   • trailhead: dark rounded square with a "P" (parking)
//   • camp: numbered teardrop pin in the day's color
//   • feature: small dot, color-coded by category
function buildCampPin(color: string, dayNumber: number): L.DivIcon {
  return L.divIcon({
    className: "rs-marker",
    html: `<div class="rs-marker-pin" style="background:${color}"><span>${dayNumber}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -26],
  });
}

const TRAILHEAD_ICON = L.divIcon({
  className: "rs-marker",
  html: `<div class="rs-marker-th"><span>P</span></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
  popupAnchor: [0, -14],
});

const FEATURE_COLOR: Record<FeatureCategory, string> = {
  peak:      "#b45309", // amber-700
  pass:      "#7c2d12", // brown
  lake:      "#0369a1", // sky-700
  waterfall: "#0e7490", // cyan-700
  viewpoint: "#a16207", // yellow-700
  meadow:    "#15803d", // green-700
};

function FitBounds({ response }: { response: PlanResponse }) {
  const map = useMap();
  useEffect(() => {
    // Include the trailhead in the bounds — it's on the curated parking-lot
    // coords, not the snapped graph node, so it can sit slightly outside the
    // route's bbox.
    const allCoords: [number, number][] = [
      [response.start_trailhead.lat, response.start_trailhead.lon],
      [response.end_trailhead.lat, response.end_trailhead.lon],
      ...response.days.flatMap((d) => d.path_coords as [number, number][]),
    ];
    if (allCoords.length > 1) {
      map.fitBounds(L.latLngBounds(allCoords), { padding: [32, 32], animate: true });
    }
  }, [response, map]);
  return null;
}

export function MapView({ response, selectedDay }: Props) {
  const dim = (day: number) => selectedDay !== null && selectedDay !== day;
  const startCoord: [number, number] = [
    response.start_trailhead.lat,
    response.start_trailhead.lon,
  ];
  const endCoord: [number, number] = [
    response.end_trailhead.lat,
    response.end_trailhead.lon,
  ];
  const isLoop = response.start_trailhead.name === response.end_trailhead.name;

  // dedupe features across days; show each only once on the map
  const featuresShown = new Map<string, { feature: PlanResponse["days"][number]["features_passed"][number]; day: number }>();
  for (const day of response.days) {
    for (const f of day.features_passed) {
      if (!featuresShown.has(f.name)) {
        featuresShown.set(f.name, { feature: f, day: day.day });
      }
    }
  }

  return (
    <MapContainer
      center={startCoord}
      zoom={11}
      scrollWheelZoom
      className="h-full w-full"
      zoomControl
    >
      <TileLayer
        url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
        attribution='Map: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA) · Data: &copy; OpenStreetMap contributors, SRTM'
        maxZoom={17}
      />
      <FitBounds response={response} />

      {/* White halo so colored lines read against the topo tiles */}
      {response.days.map((day) => (
        <Polyline
          key={`halo-${day.day}`}
          positions={day.path_coords}
          pathOptions={{ color: "white", weight: 7, opacity: dim(day.day) ? 0.2 : 0.7 }}
        />
      ))}
      {response.days.map((day) => {
        const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
        const dimmed = dim(day.day);
        return (
          <Polyline
            key={`path-${day.day}`}
            positions={day.path_coords}
            pathOptions={{
              color,
              weight: dimmed ? 3 : 4,
              opacity: dimmed ? 0.25 : 0.95,
              lineCap: "round",
              lineJoin: "round",
            }}
          />
        );
      })}

      {/* Feature dots — small, deduped, beneath markers in z-order */}
      {Array.from(featuresShown.values()).map(({ feature: f, day }) => {
        const color = FEATURE_COLOR[f.category as FeatureCategory] ?? "#525252";
        return (
          <CircleMarker
            key={`feat-${f.name}`}
            center={[f.lat, f.lon]}
            radius={5}
            pathOptions={{
              color: "white",
              weight: 1.5,
              fillColor: color,
              fillOpacity: dim(day) ? 0.25 : 0.95,
            }}
          >
            <Popup>
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                {CATEGORY_LABELS[f.category] ?? f.category}
              </div>
              <div className="text-sm font-medium text-stone-900">{f.name}</div>
              <div className="text-[11px] text-stone-500 mt-0.5">passes on Day {day}</div>
            </Popup>
          </CircleMarker>
        );
      })}

      <Marker position={startCoord} icon={TRAILHEAD_ICON}>
        <Popup>
          <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
            {isLoop ? "Trailhead — start & finish" : "Start trailhead"}
          </div>
          <div className="text-sm font-medium text-stone-900">
            {response.start_trailhead.name}
          </div>
        </Popup>
      </Marker>

      {!isLoop && (
        <Marker position={endCoord} icon={TRAILHEAD_ICON}>
          <Popup>
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              End trailhead
            </div>
            <div className="text-sm font-medium text-stone-900">
              {response.end_trailhead.name}
            </div>
          </Popup>
        </Marker>
      )}

      {response.days.map((day, i) => {
        // Skip the last-day "camp" — for loops/out-and-backs it's just the
        // return to the trailhead, already marked by the trailhead pin.
        const isReturnDay = i === response.days.length - 1 && day.camp_name === response.end_trailhead.name;
        if (isReturnDay) return null;
        const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
        return (
          <Marker
            key={`camp-${day.day}`}
            position={[day.camp_lat, day.camp_lon]}
            icon={buildCampPin(color, day.day)}
          >
            <Popup>
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Day {day.day} camp
              </div>
              <div className="text-sm font-medium text-stone-900">{day.camp_name}</div>
              <div className="text-xs text-stone-500 mt-0.5">
                {day.length_miles.toFixed(1)} mi · {day.gain_m} m gain
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
