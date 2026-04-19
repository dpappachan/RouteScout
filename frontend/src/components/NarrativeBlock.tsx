import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
}

export function NarrativeBlock({ response }: Props) {
  return (
    <section className="bg-white border border-stone-200 rounded-lg p-5">
      <header className="flex items-baseline justify-between mb-2">
        <h3 className="text-sm font-medium text-stone-900">Trip description</h3>
        <span className="text-[11px] text-stone-400">
          parse {response.elapsed_seconds.parse.toFixed(1)}s ·
          plan {response.elapsed_seconds.plan.toFixed(1)}s ·
          narrate {response.elapsed_seconds.narrate.toFixed(1)}s
        </span>
      </header>
      <div className="text-sm text-stone-800 leading-relaxed whitespace-pre-line">
        {response.narrative}
      </div>
    </section>
  );
}
