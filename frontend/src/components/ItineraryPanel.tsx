import { ChevronRight, Route } from "lucide-react";
import { useState } from "react";
import { CATEGORY_LABELS, DAY_COLORS } from "../constants";
import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
}

export function ItineraryPanel({ response }: Props) {
  const [showParser, setShowParser] = useState(false);
  return (
    <section className="bg-white border border-stone-200 rounded-xl p-5 shadow-sm rs-fade">
      <header className="flex items-center justify-between mb-4 gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500 flex items-center gap-1.5">
          <Route size={12} /> Itinerary
        </h3>
        <div className="flex items-baseline gap-2 text-[11px] text-stone-400 font-mono">
          <span>{response.days.length}d</span>
          <span>·</span>
          <span>{response.total_length_miles.toFixed(1)}mi</span>
          <span>·</span>
          <span>{response.total_gain_m}m</span>
        </div>
      </header>
      <ol className="flex flex-col gap-3">
        {response.days.map((day, i) => {
          const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
          const passed = day.features_passed.filter((f) => f.name !== day.camp_name);
          const isLast = i === response.days.length - 1;
          return (
            <li key={day.day} className="flex gap-3">
              <div className="flex flex-col items-center pt-0.5 shrink-0">
                <span
                  className="h-6 w-6 rounded-full text-white text-[10px] font-semibold flex items-center justify-center shadow-sm"
                  style={{ backgroundColor: color }}
                >
                  {day.day}
                </span>
                {!isLast && <span className="w-px flex-1 bg-stone-200 mt-1" />}
              </div>
              <div className="flex-1 pb-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-stone-900">
                    {day.camp_name}
                  </span>
                  <span className="text-[11px] text-stone-500 whitespace-nowrap font-mono">
                    {day.length_miles.toFixed(1)} mi · {day.gain_m} m
                  </span>
                </div>
                {passed.length > 0 && (
                  <p className="text-xs text-stone-500 mt-1.5 leading-relaxed">
                    {passed.slice(0, 6).map((f, idx) => (
                      <span key={f.name}>
                        <span className="text-stone-700">{f.name}</span>
                        <span className="text-stone-400">
                          {" "}
                          · {CATEGORY_LABELS[f.category] ?? f.category}
                        </span>
                        {idx < Math.min(passed.length, 6) - 1 && (
                          <span className="text-stone-300"> / </span>
                        )}
                      </span>
                    ))}
                    {passed.length > 6 && (
                      <span className="text-stone-400"> +{passed.length - 6} more</span>
                    )}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      <button
        onClick={() => setShowParser((v) => !v)}
        className="mt-4 flex items-center gap-1 text-[11px] text-stone-500 hover:text-stone-900 transition"
      >
        <ChevronRight
          size={12}
          className={`transition-transform ${showParser ? "rotate-90" : ""}`}
        />
        <span>Parser output</span>
      </button>
      {showParser && (
        <pre className="text-[11px] text-stone-600 mt-2 bg-stone-50 rounded-lg p-3 overflow-x-auto border border-stone-200">
          {JSON.stringify(response.parsed, null, 2)}
        </pre>
      )}
    </section>
  );
}
