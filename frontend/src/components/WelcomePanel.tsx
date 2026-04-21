import { useState } from "react";

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

// Personal JMT photos shot on a Fujifilm; one is picked at random per page load.
const PHOTOS = [
  { src: "/photos/jmt-1.jpeg", caption: "Lyell Canyon" },
  { src: "/photos/jmt-2.jpeg", caption: "Half Dome from Olmsted Point" },
  { src: "/photos/jmt-3.jpeg", caption: "Half Dome, late afternoon" },
  { src: "/photos/jmt-4.jpeg", caption: "Half Dome, vertical" },
  { src: "/photos/jmt-5.jpeg", caption: "The Minarets, Ansel Adams Wilderness" },
];

export function WelcomePanel({ onSample }: Props) {
  // useState's lazy initializer runs once at mount — random pick that stays
  // stable for the rest of the session, no flash on rerender.
  const [photo] = useState(() => PHOTOS[Math.floor(Math.random() * PHOTOS.length)]);

  return (
    <div className="max-w-3xl mx-auto py-6">
      <div className="relative w-full h-64 md:h-80 rounded-2xl overflow-hidden mb-8 shadow-sm bg-stone-100">
        <img
          src={photo.src}
          alt={photo.caption}
          className="absolute inset-0 w-full h-full object-cover"
          loading="eager"
          decoding="async"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-stone-900/70 via-stone-900/10 to-transparent" />
        <div className="absolute bottom-4 left-5 right-5 flex items-end justify-between gap-4">
          <h1 className="text-white text-2xl md:text-3xl font-medium tracking-tight drop-shadow">
            Plan a hike across the Sierra.
          </h1>
          <span className="hidden sm:block text-[10px] uppercase tracking-wider text-white/70">
            {photo.caption}
          </span>
        </div>
      </div>
      <p className="text-sm text-stone-600 max-w-xl">
        Type a hiking trip request in plain English — duration, region, distance,
        what you'd like to see. The planner picks a trailhead, routes a day-by-day
        path through the OpenStreetMap trail graph, and writes it up.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
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
