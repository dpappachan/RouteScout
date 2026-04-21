interface Props {
  onSample: (prompt: string) => void;
}

const EXAMPLES = [
  "3-day loop from Tuolumne camping at lakes, 9 miles a day",
  "2-day waterfall hike from Glacier Point, 8 miles a day",
  "Day hike to Half Dome",
  "Weekend summit loop from Tuolumne Meadows",
  "Easy overnight trip to a lake",
];

export function WelcomePanel({ onSample }: Props) {
  return (
    <div className="max-w-2xl mx-auto py-10">
      <h1 className="text-2xl font-medium text-stone-900 tracking-tight">
        Type a hiking trip request.
      </h1>
      <p className="mt-2 text-sm text-stone-600">
        Plain English — duration, region, distance, what you'd like to see. The
        planner picks a trailhead, routes a day-by-day path through the Yosemite
        trail graph, and writes it up.
      </p>
      <div className="mt-8 flex flex-wrap gap-2">
        {EXAMPLES.map((p) => (
          <button
            key={p}
            onClick={() => onSample(p)}
            className="text-left text-sm px-3 py-1.5 rounded-md border border-stone-300 bg-white text-stone-700 hover:border-stone-900 hover:text-stone-900 transition"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
