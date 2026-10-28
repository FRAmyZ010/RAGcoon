import { useState } from "react";
import { Link } from "react-router-dom";
import { Star, Upload } from "lucide-react";
import { MAX_ATTACHMENT_BYTES, submitFeedback } from "../services/feedbackApi";

const TYPES = ["Suggestion", "Bug", "Others"];

export default function FeedbackPage() {
  const [rating, setRating] = useState(0);
  const [type, setType] = useState("");
  const [message, setMessage] = useState("");
  const [file, setFile] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const resetForm = () => {
    setRating(0);
    setType("");
    setMessage("");
    setFile(null);
    setSubmitted(false);
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!rating) {
      setError("Please select a rating.");
      return;
    }
    if (!type) {
      setError("Please select a feedback type.");
      return;
    }
    if (!message.trim()) {
      setError("Please enter your feedback.");
      return;
    }
    if (file && file.size > MAX_ATTACHMENT_BYTES) {
      setError("Attachment is larger than 10MB");
      return;
    }

    setSending(true);
    try {
      await submitFeedback({
        name: "Anonymous",
        rating,
        feedbackType: type,
        comment: message.trim(),
        file,
      });
      setSubmitted(true);
    } catch (err) {
      setSubmitted(false);
      setError(err.message || "Could not send feedback");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f7f7f8] font-sans text-gray-800">
      <header className="flex h-14 items-center border-b border-gray-200 bg-white px-4">
        <Link to="/chat" className="text-sm font-semibold text-gray-700 hover:text-gray-900">
          Back to chat
        </Link>
        <h1 className="mx-auto pr-24 text-base font-bold text-gray-900">Feedback</h1>
      </header>

      <main className="mx-auto w-full max-w-xl px-4 py-8">
        <form onSubmit={handleSubmit} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-gray-500">
            You stay anonymous. Rating, type, and a short message are required. A file is optional.
          </p>

          <div className="mt-5">
            <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Rating</p>
            <div className="mt-1.5 flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
                  onClick={() => {
                    setRating(star);
                    setSubmitted(false);
                    setError("");
                  }}
                  className="rounded-lg p-1 hover:bg-gray-100"
                >
                  <Star className={`h-6 w-6 ${star <= rating ? "fill-amber-400 text-amber-400" : "text-gray-300"}`} />
                </button>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Type</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {TYPES.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setType(item);
                    setSubmitted(false);
                    setError("");
                  }}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                    type === item ? "bg-gray-900 text-white" : "border border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <label htmlFor="feedback-message" className="text-xs font-bold uppercase tracking-wide text-gray-500">
              Message
            </label>
            <textarea
              id="feedback-message"
              value={message}
              onChange={(event) => {
                setMessage(event.target.value);
                setSubmitted(false);
                setError("");
              }}
              placeholder="What should we know?"
              className="mt-1.5 h-28 w-full resize-none rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm outline-none focus:border-gray-400 focus:bg-white"
            />
          </div>

          {error && (
            <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <div className="mt-5">
            <p className="text-xs font-bold uppercase tracking-wide text-gray-500">File</p>
            <label className="mt-1.5 flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 text-sm text-gray-700 hover:bg-gray-50">
              <Upload className="h-4 w-4 shrink-0 text-gray-400" />
              <span className="truncate">{file ? file.name : "Choose file"}</span>
              <input
                type="file"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={resetForm}
              className="h-9 rounded-xl border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={sending}
              className="h-9 rounded-xl bg-[#2d2d2d] px-4 text-sm font-semibold text-white hover:bg-black disabled:opacity-60"
            >
              {sending ? "Sending..." : "Send feedback"}
            </button>
          </div>
        </form>
      </main>

      {submitted && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation">
          <div role="dialog" aria-modal="true" className="w-full max-w-sm rounded-xl bg-white p-4 shadow-xl">
            <h2 className="text-sm font-bold text-gray-900">Feedback sent</h2>
            <p className="mt-1 text-xs leading-5 text-gray-600">Thank you. We saved your note.</p>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={resetForm}
                className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-bold text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
