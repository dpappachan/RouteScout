import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

const STAGES = [
  { label: "Parsing your request", duration: 2800 },
  { label: "Planning route through the trail graph", duration: 1600 },
  { label: "Writing trip description", duration: 8000 },
];

export function LoadingState() {
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    setActiveIdx(0);
    const timers: ReturnType<typeof setTimeout>[] = [];
    let elapsed = 0;
    STAGES.forEach((_stage, i) => {
      if (i === 0) return;
      elapsed += STAGES[i - 1].duration;
      timers.push(setTimeout(() => setActiveIdx(i), elapsed));
    });
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="max-w-md mx-auto py-16">
      <div className="bg-white border border-stone-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-stone-500 mb-5">
          <Loader2 size={14} className="animate-spin" />
          <span>Planning your trip</span>
        </div>
        <ol className="flex flex-col gap-3.5">
          {STAGES.map((stage, i) => {
            const done = i < activeIdx;
            const active = i === activeIdx;
            return (
              <li key={stage.label} className="flex items-center gap-3">
                <span
                  className={`h-5 w-5 rounded-full flex items-center justify-center shrink-0 transition ${
                    done
                      ? "bg-brand text-white"
                      : active
                      ? "bg-stone-900 text-white rs-pulse"
                      : "bg-stone-100 text-stone-400"
                  }`}
                >
                  {done ? (
                    <Check size={12} strokeWidth={3} />
                  ) : (
                    <span className="text-[10px]">{i + 1}</span>
                  )}
                </span>
                <span
                  className={`text-sm transition ${
                    done
                      ? "text-stone-500 line-through decoration-stone-300"
                      : active
                      ? "text-stone-900 font-medium"
                      : "text-stone-400"
                  }`}
                >
                  {stage.label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
