export function Header() {
  return (
    <header className="border-b border-stone-200/80 bg-white/70 backdrop-blur-sm sticky top-0 z-[1000]">
      <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between gap-4">
        <a href="/" className="flex items-baseline gap-2.5">
          <span className="font-display text-xl tracking-tight text-stone-900">
            RouteScout
          </span>
          <span className="text-xs text-stone-500">Hiking route planner for the Sierra</span>
        </a>
        <a
          href="https://github.com/dpappachan/RouteScout"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 text-sm text-stone-600 hover:text-stone-900 transition"
          aria-label="GitHub source"
        >
          <svg height="16" width="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 .5C5.73.5.5 5.73.5 12a11.5 11.5 0 0 0 7.86 10.92c.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.31-1.28-1.66-1.28-1.66-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.68 1.25 3.34.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.18-3.09-.12-.29-.51-1.47.11-3.07 0 0 .97-.31 3.18 1.18a11.06 11.06 0 0 1 5.78 0c2.21-1.5 3.18-1.18 3.18-1.18.62 1.6.23 2.78.11 3.07.74.8 1.18 1.83 1.18 3.09 0 4.42-2.69 5.41-5.25 5.69.41.36.78 1.05.78 2.12v3.14c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5Z"/>
          </svg>
          <span className="hidden sm:inline">source</span>
        </a>
      </div>
    </header>
  );
}
