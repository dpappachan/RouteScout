import { ArrowUp } from "lucide-react";
import type { FormEvent, KeyboardEvent } from "react";

interface Props {
  prompt: string;
  onChange: (v: string) => void;
  onSubmit: (v: string) => void;
  loading: boolean;
  compact?: boolean;
}

export function PromptBar({ prompt, onChange, onSubmit, loading, compact }: Props) {
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
    <form onSubmit={handleSubmit} className="relative">
      <textarea
        className={`w-full rounded-xl border border-stone-300 bg-white px-4 ${
          compact ? "py-2.5 text-sm pr-12" : "py-3.5 pr-14 text-base"
        } resize-none shadow-sm focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand transition placeholder:text-stone-400`}
        rows={compact ? 1 : 2}
        placeholder={
          compact
            ? "Try another trip…"
            : "Describe the hike you want — \"3-day loop camping at lakes, 9 miles a day\""
        }
        value={prompt}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !prompt.trim()}
        aria-label="Plan trip"
        className={`absolute ${
          compact ? "right-2 bottom-1.5" : "right-3 bottom-3"
        } h-9 w-9 rounded-lg bg-stone-900 text-white hover:bg-stone-700 disabled:bg-stone-300 disabled:cursor-not-allowed transition flex items-center justify-center shadow-sm`}
      >
        <ArrowUp size={18} strokeWidth={2.2} />
      </button>
    </form>
  );
}
