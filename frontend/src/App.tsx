import { useCallback, useRef, useState } from "react";
import { PlanError, postPlan } from "./api";
import { ElevationChart } from "./components/ElevationChart";
import { ErrorBanner } from "./components/ErrorBanner";
import { Header } from "./components/Header";
import { ItineraryPanel } from "./components/ItineraryPanel";
import { LoadingState } from "./components/LoadingState";
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
      setPrompt(text);
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

  const handleSample = useCallback(
    (sample: string) => {
      setPrompt(sample);
      submit(sample);
    },
    [submit],
  );

  const hasResult = response !== null;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 md:px-6 py-6">
        {!hasResult && !loading && <WelcomePanel onSample={handleSample} />}

        {loading && !hasResult && <LoadingState />}

        {(hasResult || loading) && (
          <div className="mb-6 rs-fade">
            <PromptBar
              prompt={prompt}
              onChange={setPrompt}
              onSubmit={submit}
              loading={loading}
              compact
            />
          </div>
        )}

        {!hasResult && (
          <div className="max-w-3xl mx-auto mt-6">
            <PromptBar
              prompt={prompt}
              onChange={setPrompt}
              onSubmit={submit}
              loading={loading}
            />
          </div>
        )}

        {error && (
          <div className="max-w-3xl mx-auto mt-3">
            <ErrorBanner message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        {hasResult && response && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 rs-fade">
            <div className="lg:col-span-3 flex flex-col gap-4">
              <div className="bg-white border border-stone-200 rounded-xl overflow-hidden h-[500px] shadow-sm">
                <MapView response={response} />
              </div>
              <div className="bg-white border border-stone-200 rounded-xl p-5 shadow-sm">
                <ElevationChart response={response} />
              </div>
            </div>
            <div className="lg:col-span-2 flex flex-col gap-4">
              <NarrativeBlock response={response} />
              <ItineraryPanel response={response} />
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-stone-200/80 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 text-xs text-stone-500 flex flex-wrap gap-2 justify-between">
          <span>
            Trail data · OpenStreetMap · Elevation · SRTM / Open-Elevation
          </span>
          <span>Routing · A* + beam search · Language · Gemini 2.5 Flash</span>
        </div>
      </footer>
    </div>
  );
}
