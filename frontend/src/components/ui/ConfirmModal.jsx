import { useEffect } from "react";

export default function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  busy = false,
  onConfirm,
  onClose,
}) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation" onClick={busy ? undefined : onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        className="w-full max-w-sm rounded-xl bg-white p-4 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirm-modal-title" className="text-sm font-bold text-gray-900">{title}</h2>
        <p className="mt-1 text-xs leading-5 text-gray-600">{message}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" disabled={busy} onClick={onClose} className="rounded-lg border bg-white px-3 py-1.5 text-xs font-bold text-gray-700 disabled:opacity-60">
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold text-white disabled:opacity-60 ${danger ? "bg-red-600" : "bg-gray-900"}`}
          >
            {busy ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
