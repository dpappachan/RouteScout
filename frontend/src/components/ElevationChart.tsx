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

  const minElev = Math.min(...data.map((d) => d.elevation_m));
  const maxElev = Math.max(...data.map((d) => d.elevation_m));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
          Elevation profile
        </h3>
        <span className="text-[11px] text-stone-400 font-mono">
          {Math.round(minElev)}–{Math.round(maxElev)} m · {response.total_length_miles.toFixed(1)} mi
        </span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={data} margin={{ top: 6, right: 10, left: -6, bottom: 8 }}>
          <defs>
            <linearGradient id="elevFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#166534" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#166534" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" stroke="#e7e5e4" vertical={false} />
          <XAxis
            dataKey="miles"
            type="number"
            domain={[0, "dataMax"]}
            tick={{ fontSize: 10, fill: "#78716c" }}
            tickFormatter={(v: number) => `${v.toFixed(1)}`}
            axisLine={{ stroke: "#e7e5e4" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#78716c" }}
            domain={["dataMin - 50", "dataMax + 50"]}
            tickFormatter={(v: number) => `${Math.round(v)}`}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e7e5e4",
              padding: "6px 10px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.06)",
            }}
            formatter={(val, name) => {
              if (name === "elevation_m") return [`${Math.round(Number(val))} m`, "elevation"];
              return [val as string | number, name];
            }}
            labelFormatter={(miles) => `${Number(miles).toFixed(2)} mi`}
          />
          <Area
            type="monotone"
            dataKey="elevation_m"
            stroke="#166534"
            strokeWidth={1.5}
            fill="url(#elevFill)"
            isAnimationActive={false}
          />
          {boundaries.map((b) => (
            <ReferenceLine
              key={b.miles}
              x={b.miles}
              stroke={DAY_COLORS[(b.dayAfter - 1) % DAY_COLORS.length]}
              strokeDasharray="3 3"
              strokeOpacity={0.8}
              label={{
                value: `d${b.dayAfter}`,
                position: "insideTopRight",
                fontSize: 9,
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
    const series = day.elevation_series;
    for (const pt of series) {
      data.push({
        miles: +(offset + pt.miles).toFixed(3),
        elevation_m: pt.elevation_m,
        day: day.day,
      });
    }
    const dayEnd = offset + (series[series.length - 1]?.miles ?? 0);
    if (idx < response.days.length - 1) {
      boundaries.push({ miles: dayEnd, dayAfter: day.day + 1 });
    }
    offset = dayEnd;
  });
  return { data, boundaries };
}
