import L from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { DAY_COLORS } from "../constants";
import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
  selectedDay: number | null;
}

function buildPin(color: string, label: string): L.DivIcon {
  return L.divIcon({
    className: "rs-marker",
    html: `<div class="rs-marker-pin" style="background:${color}"><span>${label}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -26],
  });
}

const START_ICON = L.divIcon({
  className: "rs-marker",
  html: `<div class="rs-marker-pin rs-marker-start"><span>●</span></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -26],
});

function FitBounds({ response }: { response: PlanResponse }) {
  const map = useMap();
  useEffect(() => {
    const allCoords = response.days.flatMap((d) => d.path_coords);
    if (allCoords.length > 1) {
      const bounds = L.latLngBounds(allCoords as [number, number][]);
      map.fitBounds(bounds, { padding: [32, 32], animate: true });
    }
  }, [response, map]);
  return null;
}

export function MapView({ response, selectedDay }: Props) {
  const dim = (day: number) => selectedDay !== null && selectedDay !== day;
  const startCoord = response.days[0]?.path_coords[0];
  const center: [number, number] = startCoord ?? [37.8651, -119.5383];

  return (
    <MapContainer
      center={center}
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

      {/* White halo underneath so colored lines read against the topo tiles */}
      {response.days.map((day) => (
        <Polyline
          key={`halo-${day.day}`}
          positions={day.path_coords}
          pathOptions={{ color: "white", weight: 7, opacity: dim(day.day) ? 0.25 : 0.7 }}
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

      {startCoord && (
        <Marker position={startCoord} icon={START_ICON}>
          <Popup>
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              Start
            </div>
            <div className="text-sm font-medium text-stone-900">{response.parsed.start}</div>
          </Popup>
        </Marker>
      )}

      {response.days.map((day, i) => {
        // Skip last-day camp if it's the same as start (loop close) — start
        // marker already indicates this location
        if (
          i === response.days.length - 1 &&
          startCoord &&
          Math.abs(day.camp_lat - startCoord[0]) < 1e-4 &&
          Math.abs(day.camp_lon - startCoord[1]) < 1e-4
        ) {
          return null;
        }
        const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
        return (
          <Marker
            key={`camp-${day.day}`}
            position={[day.camp_lat, day.camp_lon]}
            icon={buildPin(color, String(day.day))}
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
