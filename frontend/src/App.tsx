import { useCallback, useRef, useState } from "react";
import { PlanError, postPlan } from "./api";
import { ElevationChart } from "./components/ElevationChart";
import { ItineraryPanel } from "./components/ItineraryPanel";
import { MapView } from "./components/MapView";
import { NarrativeBlock } from "./components/NarrativeBlock";
import { PromptBar } from "./components/PromptBar";
import { WelcomePanel } from "./components/WelcomePanel";
import type { PlanResponse } from "./types";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await postPlan(text.trim(), controller.signal);
      setResponse(result);
    } catch (err) {
      if (controller.signal.aborted) return;
      if (err instanceof PlanError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [loading]);

  const handleSample = useCallback((sample: string) => {
    setPrompt(sample);
    submit(sample);
  }, [submit]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-stone-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between gap-4">
          <div>
            <div className="flex items-baseline gap-3">
              <h1 className="text-2xl font-semibold tracking-tight text-stone-900">RouteScout</h1>
              <span className="text-sm text-stone-500">
                AI hiking route planner for Yosemite
              </span>
            </div>
          </div>
          <a
            href="https://github.com/dpappachan/RouteScout"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-stone-500 hover:text-stone-900 transition"
          >
            source →
          </a>
        </div>
      </header>

      <div className="border-b border-stone-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <PromptBar
            prompt={prompt}
            onChange={setPrompt}
            onSubmit={submit}
            onSample={handleSample}
            loading={loading}
          />
          {error && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          )}
        </div>
      </div>

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        {!response && !loading && <WelcomePanel onSample={handleSample} />}

        {response && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 flex flex-col gap-4">
              <div className="bg-white border border-stone-200 rounded-lg overflow-hidden h-[460px]">
                <MapView response={response} />
              </div>
              <div className="bg-white border border-stone-200 rounded-lg p-4">
                <ElevationChart response={response} />
              </div>
            </div>
            <div className="lg:col-span-2 flex flex-col gap-4">
              <NarrativeBlock response={response} />
              <ItineraryPanel response={response} />
            </div>
          </div>
        )}

        {loading && !response && (
          <div className="text-center py-20">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-stone-300 border-t-stone-900" />
            <div className="mt-3 text-sm text-stone-500">Planning your trip…</div>
          </div>
        )}
      </main>

      <footer className="border-t border-stone-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-3 text-xs text-stone-500 flex justify-between">
          <span>Trail data: OpenStreetMap · Elevation: SRTM via Open-Elevation</span>
          <span>Routing: A* + beam search · NL: Gemini 2.5 Flash</span>
        </div>
      </footer>
    </div>
  );
}
