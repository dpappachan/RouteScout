import { AlertTriangle, X } from "lucide-react";

interface Props {
  message: string;
  onDismiss: () => void;
}

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 rs-fade">
      <AlertTriangle size={16} className="shrink-0 mt-0.5 text-amber-600" />
      <div className="flex-1 leading-relaxed">{message}</div>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="shrink-0 text-amber-700 hover:text-amber-900 transition"
      >
        <X size={16} />
      </button>
    </div>
  );
}
