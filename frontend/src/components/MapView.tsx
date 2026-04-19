import L from "leaflet";
import markerIconRetina from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useEffect } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { DAY_COLORS } from "../constants";
import type { PlanResponse } from "../types";

// Leaflet bundles its marker icons via image URLs that bundlers can't resolve
// without this tweak. Fixing once at module load.
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIconRetina,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

interface Props {
  response: PlanResponse;
}

function FitBounds({ response }: { response: PlanResponse }) {
  const map = useMap();
  useEffect(() => {
    const allCoords = response.days.flatMap((d) => d.path_coords);
    if (allCoords.length > 1) {
      const bounds = L.latLngBounds(allCoords.map(([lat, lon]) => [lat, lon] as [number, number]));
      map.fitBounds(bounds, { padding: [28, 28] });
    }
  }, [response, map]);
  return null;
}

export function MapView({ response }: Props) {
  const startCoord = response.days[0]?.path_coords[0];
  const center: [number, number] = startCoord ?? [37.8651, -119.5383];

  return (
    <MapContainer
      center={center}
      zoom={11}
      scrollWheelZoom
      className="h-full w-full"
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> contributors'
      />
      <FitBounds response={response} />

      {response.days.map((day) => {
        const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
        return (
          <Polyline
            key={`path-${day.day}`}
            positions={day.path_coords}
            pathOptions={{ color, weight: 4, opacity: 0.9 }}
          />
        );
      })}

      {startCoord && (
        <Marker position={startCoord}>
          <Popup>
            <strong>Start</strong>
            <br />
            {response.parsed.start}
          </Popup>
        </Marker>
      )}

      {response.days.map((day) => (
        <Marker key={`camp-${day.day}`} position={[day.camp_lat, day.camp_lon]}>
          <Popup>
            <strong>Day {day.day} camp</strong>
            <br />
            {day.camp_name}
            <br />
            <span className="text-xs">
              {day.length_miles.toFixed(1)} mi · {day.gain_m} m gain
            </span>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
