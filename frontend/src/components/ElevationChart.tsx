import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DAY_COLORS } from "../constants";
import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
}

interface Point {
  miles: number;
  elevation_m: number;
  day: number;
}

export function ElevationChart({ response }: Props) {
  const { data, boundaries } = buildSeries(response);
  if (data.length === 0) return null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <h3 className="text-sm font-medium text-stone-900">Elevation profile</h3>
        <span className="text-xs text-stone-500">
          {response.total_length_miles.toFixed(1)} mi · {response.total_gain_m} m gain
        </span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data} margin={{ top: 6, right: 6, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="elevFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#78716c" stopOpacity={0.6} />
              <stop offset="100%" stopColor="#78716c" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
          <XAxis
            dataKey="miles"
            type="number"
            domain={[0, "dataMax"]}
            tick={{ fontSize: 11, fill: "#78716c" }}
            tickFormatter={(v: number) => v.toFixed(1)}
            label={{ value: "miles", position: "insideBottom", offset: -2, fontSize: 11, fill: "#78716c" }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#78716c" }}
            domain={["dataMin - 50", "dataMax + 50"]}
            tickFormatter={(v: number) => `${Math.round(v)}`}
            label={{ value: "m", position: "insideLeft", offset: 14, fontSize: 11, fill: "#78716c" }}
          />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e7e5e4" }}
            formatter={(val, name) => {
              if (name === "elevation_m") return [`${Math.round(Number(val))} m`, "elevation"];
              return [val as string | number, name];
            }}
            labelFormatter={(miles) => `${Number(miles).toFixed(2)} mi`}
          />
          <Area
            type="monotone"
            dataKey="elevation_m"
            stroke="#44403c"
            strokeWidth={1.5}
            fill="url(#elevFill)"
            isAnimationActive={false}
          />
          {boundaries.map((b) => (
            <ReferenceLine
              key={b.miles}
              x={b.miles}
              stroke={DAY_COLORS[(b.dayAfter - 1) % DAY_COLORS.length]}
              strokeDasharray="4 2"
              label={{
                value: `day ${b.dayAfter}`,
                position: "insideTopRight",
                fontSize: 10,
                fill: DAY_COLORS[(b.dayAfter - 1) % DAY_COLORS.length],
              }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildSeries(response: PlanResponse): {
  data: Point[];
  boundaries: { miles: number; dayAfter: number }[];
} {
  const data: Point[] = [];
  const boundaries: { miles: number; dayAfter: number }[] = [];
  let offset = 0;
  response.days.forEach((day, idx) => {
    const { path_cumulative_miles: miles, path_elevations_m: elevs } = day;
    for (let i = 0; i < miles.length; i++) {
      data.push({
        miles: +(offset + miles[i]).toFixed(3),
        elevation_m: elevs[i],
        day: day.day,
      });
    }
    const dayEnd = offset + (miles[miles.length - 1] ?? 0);
    if (idx < response.days.length - 1) {
      boundaries.push({ miles: dayEnd, dayAfter: day.day + 1 });
    }
    offset = dayEnd;
  });
  return { data, boundaries };
}
