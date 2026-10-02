import { useState } from "react";
import { Pencil, Star, Upload } from "lucide-react";

export default function FeedbackPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState(false);
  const [phone, setPhone] = useState(false);
  const [rating, setRating] = useState(0);
  const [type, setType] = useState("");
  const [message, setMessage] = useState("");
  const [file, setFile] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const resetForm = () => {
    setName("");
    setEmail(false);
    setPhone(false);
    setRating(0);
    setType("");
    setMessage("");
    setFile(null);
    setSubmitted(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!name.trim()) {
      alert("Please enter your name.");
      return;
    }

    if (!rating) {
      alert("Please select a rating.");
      return;
    }

    if (!type) {
      alert("Please select a feedback type.");
      return;
    }

    if (!message.trim()) {
      alert("Please enter your feedback.");
      return;
    }

    setSubmitted(true);
  };

  return (
    <div className="min-h-[calc(100vh-2rem)] flex items-start justify-center p-4">
      <div className="w-full max-w-[900px] bg-[#303030] rounded-md shadow-xl overflow-hidden">
        <div className="h-11 bg-[#252525] flex items-center justify-center">
          <h1 className="text-white text-base sm:text-lg font-medium tracking-wide">
            Feedback
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="p-4 sm:p-6 md:p-7 space-y-5">
          <div>
            <div className="flex items-center gap-3">
              <label className="w-8 shrink-0 text-white text-xs sm:text-sm font-medium">
                Name
              </label>

              <div className="relative flex-1">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setSubmitted(false);
                  }}
                  className="w-full h-9 sm:h-10 rounded-md bg-[#f7f7f7] text-[#333] px-3 pr-9 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-yellow-400"
                />
                <Pencil className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <span className="w-8 text-white text-xs sm:text-sm font-medium">
              Contact
            </span>

            <label className="flex items-center gap-2 text-white text-[10px] sm:text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={email}
                onChange={(e) => setEmail(e.target.checked)}
                className="w-3.5 h-3.5 accent-yellow-400 cursor-pointer"
              />
              Gmail
            </label>

            <label className="flex items-center gap-2 text-white text-[10px] sm:text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={phone}
                onChange={(e) => setPhone(e.target.checked)}
                className="w-3.5 h-3.5 accent-yellow-400 cursor-pointer"
              />
              Phone number
            </label>
          </div>

          <div className="flex items-center gap-4">
            <span className="w-8 shrink-0" />

            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
                  onClick={() => {
                    setRating(star);
                    setSubmitted(false);
                  }}
                  className="p-0.5 hover:scale-110 transition-transform"
                >
                  <Star
                    className={`w-4 h-4 sm:w-5 sm:h-5 ${
                      star <= rating
                        ? "fill-yellow-400 text-yellow-400"
                        : "text-yellow-400"
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <span className="w-8 text-white text-xs sm:text-sm font-medium">
              Type
            </span>

            {["Suggestion", "Bug", "Others"].map((item) => (
              <label
                key={item}
                className="flex items-center gap-2 text-white text-[10px] sm:text-xs cursor-pointer"
              >
                <input
                  type="radio"
                  name="feedback-type"
                  value={item}
                  checked={type === item}
                  onChange={(e) => {
                    setType(e.target.value);
                    setSubmitted(false);
                  }}
                  className="w-3.5 h-3.5 accent-yellow-400 cursor-pointer"
                />
                {item}
              </label>
            ))}
          </div>

          <div>
            <textarea
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                setSubmitted(false);
              }}
              placeholder=""
              className="w-full h-24 sm:h-28 md:h-32 resize-none rounded-md bg-[#f7f7f7] text-[#333] p-3 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-yellow-400"
            />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <span className="text-white text-xs sm:text-sm font-medium">
              File
            </span>

            <label className="inline-flex items-center gap-2 w-full sm:w-[185px] h-9 rounded-md bg-[#f7f7f7] text-[#222] px-2.5 text-xs cursor-pointer hover:bg-white transition">
              <Upload className="w-4 h-4" />
              <span className="truncate">
                {file ? file.name : "Choose file"}
              </span>
              <input
                type="file"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>

          {submitted && (
            <div className="rounded-md border border-green-400/40 bg-green-500/10 px-3 py-2 text-xs text-green-200">
              Feedback sent successfully.
            </div>
          )}

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-5 pt-1">
            <button
              type="submit"
              className="w-full sm:w-[225px] h-10 rounded-md bg-[#f2d331] hover:bg-[#e4c52a] active:scale-[0.99] text-white text-xs sm:text-sm font-medium transition flex items-center justify-center gap-2 shadow-sm"
            >
              <Upload className="w-4 h-4" />
              Send Feedback
            </button>

            <button
              type="button"
              onClick={resetForm}
              className="w-full sm:w-[125px] h-10 rounded-md bg-[#242424] hover:bg-[#1e1e1e] text-white text-xs sm:text-sm transition"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
