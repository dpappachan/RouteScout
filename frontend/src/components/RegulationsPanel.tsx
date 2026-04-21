import { Info } from "lucide-react";
import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
}

const DIFFICULTY_STYLE: Record<string, string> = {
  easy: "bg-green-50 text-green-800 border-green-200",
  moderate: "bg-amber-50 text-amber-800 border-amber-200",
  strenuous: "bg-orange-50 text-orange-800 border-orange-200",
  "very strenuous": "bg-red-50 text-red-800 border-red-200",
};

export function RegulationsPanel({ response }: Props) {
  const totalHours = response.estimated_hours_per_day.reduce((a, b) => a + b, 0);
  const diffClass = DIFFICULTY_STYLE[response.difficulty] ?? DIFFICULTY_STYLE.moderate;

  return (
    <section className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm rs-fade">
      <header className="flex items-center justify-between mb-3 gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500 flex items-center gap-1.5">
          <Info size={12} /> Trip details &amp; regulations
        </h3>
        <span
          className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${diffClass} capitalize`}
        >
          {response.difficulty}
        </span>
      </header>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs mb-3">
        <dt className="text-stone-500">Total distance</dt>
        <dd className="text-stone-900 font-medium text-right">
          {response.total_length_miles.toFixed(1)} mi
        </dd>
        <dt className="text-stone-500">Total elevation gain</dt>
        <dd className="text-stone-900 font-medium text-right">
          {response.total_gain_m} m
        </dd>
        <dt className="text-stone-500">Estimated time</dt>
        <dd className="text-stone-900 font-medium text-right">
          ~{totalHours.toFixed(1)} h hiking
        </dd>
      </dl>

      <ul className="text-xs text-stone-700 leading-relaxed space-y-1.5 list-disc pl-4">
        {response.regulations.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
