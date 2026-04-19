import { DAY_COLORS } from "../constants";
import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
}

export function ItineraryPanel({ response }: Props) {
  return (
    <section className="bg-white border border-stone-200 rounded-lg p-4">
      <header className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-medium text-stone-900">Itinerary</h3>
        <span className="text-xs text-stone-500">
          {response.days.length} days · {response.total_length_miles.toFixed(1)} mi ·{" "}
          {response.total_gain_m} m gain
        </span>
      </header>
      <ol className="flex flex-col gap-3">
        {response.days.map((day) => {
          const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
          const passed = day.features_passed.filter((f) => f.name !== day.camp_name);
          return (
            <li key={day.day} className="flex gap-3">
              <div className="flex flex-col items-center pt-0.5">
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {day.day < response.days.length && (
                  <span className="w-px flex-1 bg-stone-200 mt-1" />
                )}
              </div>
              <div className="flex-1 pb-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-stone-900">
                    Day {day.day} → {day.camp_name}
                  </span>
                  <span className="text-xs text-stone-500 whitespace-nowrap">
                    {day.length_miles.toFixed(1)} mi · {day.gain_m} m
                  </span>
                </div>
                {passed.length > 0 && (
                  <p className="text-xs text-stone-600 mt-1 leading-relaxed">
                    passes{" "}
                    {passed.slice(0, 5).map((f, i) => (
                      <span key={f.name}>
                        <span className="text-stone-900">{f.name}</span>
                        <span className="text-stone-400"> ({f.category})</span>
                        {i < Math.min(passed.length, 5) - 1 && ", "}
                      </span>
                    ))}
                    {passed.length > 5 && (
                      <span className="text-stone-400"> +{passed.length - 5} more</span>
                    )}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <details className="mt-4">
        <summary className="text-xs text-stone-500 cursor-pointer hover:text-stone-900">
          parser output
        </summary>
        <pre className="text-[11px] text-stone-600 mt-2 bg-stone-50 rounded p-2 overflow-x-auto">
{JSON.stringify(response.parsed, null, 2)}
        </pre>
      </details>
    </section>
  );
}
