import type { FormEvent, KeyboardEvent } from "react";

interface Props {
  prompt: string;
  onChange: (v: string) => void;
  onSubmit: (v: string) => void;
  onSample: (v: string) => void;
  loading: boolean;
}

const SAMPLE_PROMPTS = [
  "3-day loop from Tuolumne Pass camping at lakes, 9 miles a day",
  "2-day waterfall hike around Glacier Point, 8 miles a day",
  "3-day summit loop from Tuolumne Pass, 10 miles a day",
];

export function PromptBar({ prompt, onChange, onSubmit, onSample, loading }: Props) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(prompt);
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      onSubmit(prompt);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex gap-2">
        <textarea
          className="flex-1 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-stone-900 focus:border-stone-900 transition"
          rows={2}
          placeholder="Describe your trip — e.g., '3-day loop in the Tuolumne high country camping at lakes, around 9 miles a day'"
          value={prompt}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="px-5 rounded-md bg-stone-900 text-white text-sm font-medium hover:bg-stone-700 disabled:bg-stone-300 disabled:cursor-not-allowed transition"
        >
          {loading ? "Planning…" : "Plan"}
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-stone-500 mr-1 self-center">try:</span>
        {SAMPLE_PROMPTS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onSample(s)}
            disabled={loading}
            className="text-xs px-2.5 py-1 rounded-full border border-stone-300 text-stone-700 hover:border-stone-900 hover:text-stone-900 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {s}
          </button>
        ))}
      </div>
    </form>
  );
}
