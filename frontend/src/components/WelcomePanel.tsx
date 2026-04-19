import { ArrowRight, Droplets, Mountain, Waves } from "lucide-react";

interface Props {
  onSample: (prompt: string) => void;
}

const EXAMPLES = [
  {
    prompt: "3-day loop from Tuolumne Pass camping at lakes, 9 miles a day",
    tag: "lakes",
    desc: "High-country alpine lake circuit",
    Icon: Waves,
  },
  {
    prompt: "2-day waterfall hike around Glacier Point, 8 miles a day",
    tag: "waterfalls",
    desc: "Valley rim falls and viewpoints",
    Icon: Droplets,
  },
  {
    prompt: "3-day summit loop from Tuolumne Pass, 10 miles a day",
    tag: "peaks",
    desc: "Dome and summit scramble",
    Icon: Mountain,
  },
];

export function WelcomePanel({ onSample }: Props) {
  return (
    <div className="max-w-3xl mx-auto py-10">
      <p className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-brand bg-brand-soft rounded-full px-3 py-1">
        Now available · Yosemite National Park
      </p>
      <h1 className="font-display text-5xl md:text-6xl leading-[1.05] tracking-tight text-stone-900 mt-5">
        Describe the trip. <br />
        <em className="text-stone-600">We'll plan the route.</em>
      </h1>
      <p className="mt-5 text-lg text-stone-600 max-w-xl">
        Type a natural-language hiking request. RouteScout parses it, plans
        a day-by-day route across real Yosemite trail data, and writes the
        trip up for you.
      </p>
      <div className="mt-10 grid sm:grid-cols-3 gap-3">
        {EXAMPLES.map(({ prompt, tag, desc, Icon }) => (
          <button
            key={prompt}
            onClick={() => onSample(prompt)}
            className="group text-left bg-white border border-stone-200 rounded-xl p-4 hover:border-stone-900 hover:shadow-md transition-all"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="h-9 w-9 rounded-lg bg-stone-100 text-stone-700 flex items-center justify-center group-hover:bg-brand group-hover:text-white transition">
                <Icon size={17} />
              </span>
              <ArrowRight
                size={16}
                className="text-stone-400 group-hover:text-stone-900 group-hover:translate-x-0.5 transition"
              />
            </div>
            <div className="text-xs uppercase tracking-wider text-stone-500 font-medium">
              {tag}
            </div>
            <div className="text-sm text-stone-900 mt-1 font-medium">{desc}</div>
            <div className="text-xs text-stone-500 mt-2 leading-relaxed">
              "{prompt}"
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
