import { Clock } from "lucide-react";
import type { PlanResponse } from "../types";

interface Props {
  response: PlanResponse;
}

export function NarrativeBlock({ response }: Props) {
  const total =
    response.elapsed_seconds.parse +
    response.elapsed_seconds.plan +
    response.elapsed_seconds.narrate;

  return (
    <section className="bg-white border border-stone-200 rounded-xl p-5 shadow-sm rs-fade">
      <header className="flex items-center justify-between mb-3 gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
          Trip description
        </h3>
        <span className="flex items-center gap-1 text-[11px] text-stone-400 font-mono">
          <Clock size={10} /> {total.toFixed(1)}s
        </span>
      </header>
      <div className="text-[15px] text-stone-800 leading-relaxed whitespace-pre-line font-normal">
        {response.narrative}
      </div>
      <div className="mt-4 pt-3 border-t border-stone-100 text-[11px] text-stone-400 font-mono flex gap-3">
        <span>parse {response.elapsed_seconds.parse.toFixed(1)}s</span>
        <span>plan {response.elapsed_seconds.plan.toFixed(1)}s</span>
        <span>narrate {response.elapsed_seconds.narrate.toFixed(1)}s</span>
      </div>
    </section>
  );
}
