interface Props {
  onSample: (prompt: string) => void;
}

const EXAMPLES = [
  "3-day loop from Tuolumne Pass camping at lakes, 9 miles a day",
  "2-day waterfall hike around Glacier Point, 8 miles a day",
  "3-day summit loop from Tuolumne Pass, 10 miles a day",
];

export function WelcomePanel({ onSample }: Props) {
  return (
    <div className="max-w-2xl mx-auto text-center py-16">
      <h2 className="text-3xl font-medium text-stone-900 tracking-tight">
        Describe the hike you want.
      </h2>
      <p className="mt-3 text-stone-600">
        RouteScout parses your prompt, plans a day-by-day route across real Yosemite
        trail data, and writes up the trip. Hit one of the examples below or type your own.
      </p>
      <div className="mt-8 flex flex-col gap-2">
        {EXAMPLES.map((p) => (
          <button
            key={p}
            onClick={() => onSample(p)}
            className="text-left px-4 py-3 rounded-lg border border-stone-200 bg-white hover:border-stone-900 hover:shadow-sm transition text-sm text-stone-700"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
