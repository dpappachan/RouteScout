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
  "/photos/jmt-1.jpeg",
  "/photos/jmt-2.jpeg",
  "/photos/jmt-3.jpeg",
  "/photos/jmt-4.jpeg",
  "/photos/jmt-5.jpeg",
];

export function WelcomePanel({ onSample }: Props) {
  // useState's lazy initializer runs once at mount — random pick that stays
  // stable for the rest of the session, no flash on rerender.
  const [photo] = useState(() => PHOTOS[Math.floor(Math.random() * PHOTOS.length)]);

  return (
    <div className="max-w-3xl mx-auto py-6">
      <h1 className="text-2xl md:text-3xl font-medium tracking-tight text-stone-900 mb-5">
        Plan a hike across the Sierra.
      </h1>
      <div className="relative w-full h-56 md:h-72 rounded-2xl overflow-hidden mb-6 shadow-sm bg-stone-100">
        <img
          src={photo}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
          loading="eager"
          decoding="async"
        />
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
