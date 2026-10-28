import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CircleHelp, LayoutDashboard, FolderClosed, MessageSquare, LogOut, Sliders } from "lucide-react";
import { clearAuth } from "../services/authApi";
import {
  applyPreset,
  fetchIntents,
  runBenchmark,
  fetchLlms,
  fetchRag,
  pingLlm,
  resetIntents,
  saveIntent,
  setActiveLlm as activateLlm,
} from "../services/aiConfigApi";

function Hint({ text }) {
  if (!text) return null;
  return (
    <span className="group relative inline-flex">
      <button type="button" className="rounded-full text-gray-400 hover:text-gray-700" aria-label={text}>
        <CircleHelp className="h-3.5 w-3.5" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-30 mb-1.5 hidden w-64 rounded-lg bg-gray-900 px-2.5 py-1.5 text-left text-[11px] font-normal leading-snug text-white shadow-lg group-hover:block group-focus-within:block"
      >
        {text}
      </span>
    </span>
  );
}

const TABS = ["Intent Tuning", "RAG Presets", "Multi-LLM", "Benchmark"];
const INTENT_ORDER = [
  "FACTOID",
  "FACTUAL_LOOKUP",
  "DEEP_DIVE",
  "EXPLANATION",
  "COMPARISON",
  "RECOMMENDATION",
  "EXPLORATORY",
  "CODE",
];
const INTENT_COPY = {
  FACTOID: ["Specific facts", "Short questions, such as who advised a project or which chip it uses."],
  FACTUAL_LOOKUP: ["Keyword lookup", "Find projects by hardware or technology, such as which projects use the SX1276."],
  DEEP_DIVE: ["Deep analysis", "Methods, experiment steps, and results."],
  EXPLANATION: ["Explanation", "How a system or technical idea works."],
  COMPARISON: ["Comparison", "Compare two or more projects."],
  RECOMMENDATION: ["Recommendation", "Suggest similar or follow-up projects."],
  EXPLORATORY: ["Corpus survey", "Broad questions across the whole archive."],
  CODE: ["Code", "Example code or algorithms."],
};
const NUMBER_FIELDS = [
  ["top_k", "Top K", "How many chunks are retrieved before reranking. Higher finds more and is slower."],
  ["rerank_top_n", "Rerank top N", "How many of those chunks the second-pass ranker keeps. This pass is slower and more precise."],
  ["min_score", "Minimum score", "Chunks below this score are dropped once another chunk is already kept. Exploratory uses -1 so nothing is dropped."],
  ["max_context_chunks", "Max context chunks", "Maximum chunks sent to the model. This caps how many sources the chat can show."],
  ["max_chunks_per_project", "Max chunks per project", "Stops one project from using the whole context during a comparison."],
  ["max_total_projects", "Max projects", "Maximum number of projects included in one answer."],
  ["temperature", "Temperature", "How freely the model phrases the answer. 0 stays closest to the documents. An active preset replaces this value."],
];
const TOGGLES = [
  ["enable_hybrid", "Hybrid search", "Search by meaning and by the exact words. Off uses meaning only, so chip names and titles are easier to miss."],
  ["enable_boilerplate_filter", "Boilerplate filter", "Drop tables of contents, reference lists, and signature lines before the model writes."],
  ["enable_fast_path", "Fast path", "Answer pure metadata questions, such as advisor or year, from document metadata without a vector search."],
  ["preserve_raw_code", "Preserve raw code", "Saved with this intent. The answer path does not read this switch yet. CODE questions already keep chunks from the same project."],
];
const RUBRIC = [
  ["5", "Complete", "The answer is complete and the numbers are right", "Cites the project name or page"],
  ["4", "Mostly correct", "The substance is there, with a small gap", "No false information"],
  ["3", "Partial", "Answers only part of the question", "Does not contradict the documents, but evidence is thin"],
  ["2", "Off topic", "Retrieves an unrelated project", "Cites the wrong document"],
  ["1", "Failed", "Wrong answer or invented facts", "Hallucination or a system error"],
];
const CASES = [
  ["What does Ajarn Surapol supervise?", "FACTUAL_LOOKUP", "The model fixes the typo, then finds the advisor."],
  ["Which projects use the SX1276 module?", "FACTUAL_LOOKUP", "Exact-word search retrieves the hardware name."],
  ["What are the steps and experiments of The LoRaWAN?", "DEEP_DIVE", "Drop the table of contents, then rank the methods section."],
  ["Who advises The LoRaWAN?", "FACTOID", "Answer from metadata without calling the model."],
  ["What type of system is The LoRaWAN?", "EXPLANATION", "Use the extracted project type."],
  ["Does The LoRaWAN connect to Line Notify?", "FACTOID", "Refuse when the documents do not say so."],
  ["Compare The LoRaWAN and BSLD on purpose and hardware.", "COMPARISON", "Split the context quota across two projects."],
  ["What hardware does this project use?", "DEEP_DIVE", "Remember the project from the previous question."],
];

export default function AIconfig() {
  const navigate = useNavigate();
  const [tab, setTab] = useState(TABS[0]);
  const [intents, setIntents] = useState({});
  const [selected, setSelected] = useState("FACTOID");
  const [draft, setDraft] = useState(null);
  const [presets, setPresets] = useState({});
  const [activePreset, setActivePreset] = useState("");
  const [profiles, setProfiles] = useState([]);
  const [activeLlm, setActiveLlm] = useState(null);
  const [pings, setPings] = useState({});
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [baselineName, setBaselineName] = useState("precision_hybrid");
  const [candidateName, setCandidateName] = useState("fast_mode");
  const [benchmark, setBenchmark] = useState(null);

  const notify = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 4000);
  };

  useEffect(() => {
    fetchIntents()
      .then((data) => {
        setIntents(data.intents || {});
        setDraft(data.intents?.FACTOID || null);
      })
      .catch((err) => setError(err.message));
    fetchRag()
      .then((data) => {
        setPresets(data.available_presets || {});
        setActivePreset(data.active_config?.profile_name || "");
      })
      .catch(() => {});
    fetchLlms()
      .then((data) => {
        setProfiles(data.profiles || []);
        setActiveLlm(data.active || null);
      })
      .catch(() => {});
  }, []);

  const chooseIntent = (key) => {
    setSelected(key);
    setDraft(intents[key] ? { ...intents[key] } : null);
  };

  const updateDraft = (field, value) => setDraft((current) => ({ ...current, [field]: value }));

  const onSaveIntent = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = {
        top_k: Number(draft.top_k),
        rerank_top_n: Number(draft.rerank_top_n),
        min_score: Number(draft.min_score),
        max_context_chunks: Number(draft.max_context_chunks),
        max_chunks_per_project: Number(draft.max_chunks_per_project),
        max_total_projects: Number(draft.max_total_projects),
        temperature: Number(draft.temperature),
        enable_fast_path: Boolean(draft.enable_fast_path),
        enable_hybrid: Boolean(draft.enable_hybrid),
        enable_boilerplate_filter: Boolean(draft.enable_boilerplate_filter),
        preserve_raw_code: Boolean(draft.preserve_raw_code),
        custom_system_instruction: draft.custom_system_instruction || null,
      };
      const saved = await saveIntent(selected, payload);
      setIntents((current) => ({ ...current, [selected]: saved.config }));
      setDraft(saved.config);
      notify(`Saved ${selected}. The next question of this intent uses these values.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onReset = async () => {
    setBusy(true);
    try {
      const data = await resetIntents();
      setIntents(data.intents || {});
      setDraft(data.intents?.[selected] || null);
      notify("Restored the default intent settings.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onPreset = async (name) => {
    setBusy(true);
    try {
      const data = await applyPreset(name);
      setActivePreset(data.active_preset);
      notify(`Switched the active preset to ${name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onSelectModel = async (profile) => {
    setBusy(true);
    try {
      const data = await activateLlm(profile.provider, profile.model);
      setActiveLlm(data.active);
      notify(`The next question uses ${profile.model}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onPing = async (profile) => {
    setPings((current) => ({ ...current, [profile.id]: { status: "checking" } }));
    try {
      const data = await pingLlm(profile.provider, profile.model);
      setPings((current) => ({ ...current, [profile.id]: data }));
    } catch (err) {
      setPings((current) => ({ ...current, [profile.id]: { status: "offline", message: err.message } }));
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 text-sm text-gray-800">
      <aside className="flex w-56 shrink-0 flex-col justify-between bg-[#2d2d2d] p-3 text-white">
        <div>
          <div className="mb-4 flex items-center gap-2 font-bold">
            <span>🦝</span>
            <span>RAGcoon</span>
          </div>
          <nav className="space-y-1">
            <Link className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10" to="/dashboard"><LayoutDashboard className="h-3.5 w-3.5" />Dashboard</Link>
            <Link className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10" to="/documents"><FolderClosed className="h-3.5 w-3.5" />Documents</Link>
            <Link className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10" to="/feedback-admin"><MessageSquare className="h-3.5 w-3.5" />Feedback</Link>
            <span className="flex items-center gap-2 rounded-lg bg-white px-2.5 py-1.5 font-bold text-gray-900"><Sliders className="h-3.5 w-3.5" />AI Configuration</span>
            <Link className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-gray-300 hover:bg-white/10" to="/chat"><MessageSquare className="h-3.5 w-3.5" />Chat Workspace</Link>
          </nav>
        </div>
        <button
          type="button"
          onClick={() => { clearAuth(); navigate("/login", { replace: true }); }}
          className="flex w-full items-center justify-between rounded-lg bg-white px-2.5 py-1.5 font-bold text-gray-900"
        >
          Log Out <LogOut className="h-3.5 w-3.5" />
        </button>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto p-5">
        <h1 className="mb-4 flex items-center gap-2 text-xl font-bold">
          AI Configuration
          <Hint text="Saved values apply to the next chat question. A green preset overrides per-intent retrieval." />
        </h1>
        <div className="mb-4 flex flex-wrap gap-2">
          {TABS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold ${tab === item ? "bg-gray-900 text-white" : "bg-white text-gray-700"}`}
            >
              {item}
            </button>
          ))}
        </div>
        {error && <p className="mb-3 text-sm font-semibold text-red-700">{error}</p>}

        {tab === "Intent Tuning" && draft && (
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {INTENT_ORDER.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => chooseIntent(key)}
                  className={`rounded-xl border p-3 text-left ${selected === key ? "border-indigo-700 bg-indigo-700 text-white" : "border-gray-200 bg-white"}`}
                >
                  <div className="text-xs font-bold">{key}</div>
                  <div className={`text-[11px] ${selected === key ? "text-indigo-100" : "text-gray-600"}`}>{INTENT_COPY[key]?.[0]}</div>
                </button>
              ))}
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center gap-1 text-xs font-semibold">
                {INTENT_COPY[selected]?.[0]}
                <Hint text={INTENT_COPY[selected]?.[1]} />
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {NUMBER_FIELDS.map(([field, label, hint]) => (
                  <div key={field}>
                    <div className="flex items-center gap-1 text-xs font-semibold">
                      <label htmlFor={`intent-${field}`}>{label}</label>
                      <Hint text={hint} />
                    </div>
                    <input
                      id={`intent-${field}`}
                      className="mt-1 w-full rounded-lg border px-3 py-2 text-xs font-normal"
                      value={draft[field] ?? ""}
                      onChange={(event) => updateDraft(field, event.target.value)}
                    />
                  </div>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
                {TOGGLES.map(([field, label, hint]) => (
                  <div key={field} className="flex items-center gap-1 text-xs">
                    <label className="flex items-center gap-2 font-semibold">
                      <input type="checkbox" checked={Boolean(draft[field])} onChange={(event) => updateDraft(field, event.target.checked)} />
                      {label}
                    </label>
                    <Hint text={hint} />
                  </div>
                ))}
              </div>
              <div className="mt-3">
                <div className="flex items-center gap-1 text-xs font-semibold">
                  <label htmlFor="intent-instruction">Extra instruction</label>
                  <Hint text="Appended to the system prompt for this intent only. An active preset can replace the prompt style." />
                </div>
                <textarea
                  id="intent-instruction"
                  rows={3}
                  placeholder="Example: answer in a Markdown table"
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-xs font-normal"
                  value={draft.custom_system_instruction || ""}
                  onChange={(event) => updateDraft("custom_system_instruction", event.target.value)}
                />
              </div>
              <div className="mt-3 flex items-center gap-2">
                <button type="button" disabled={busy} onClick={onSaveIntent} className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-60">
                  {busy ? "Saving..." : "Save Intent"}
                </button>
                <button type="button" disabled={busy} onClick={onReset} className="rounded-lg border px-4 py-2 text-xs font-bold">
                  Reset all
                </button>
                <Hint text="Save Intent writes this card only. Reset all restores the eight default intents." />
              </div>
            </div>
          </div>
        )}

        {tab === "RAG Presets" && (
          <div className="grid gap-3 md:grid-cols-2">
            {Object.values(presets).map((preset) => {
              const active = activePreset === preset.profile_name;
              return (
              <div key={preset.profile_name} className="rounded-xl bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="flex items-center gap-1 font-bold">
                    {preset.profile_name}
                    <Hint text={active
                      ? "The next question uses this mode's top_k, quotas, filters, temperature, and answer length. There is no control here to return to per-intent settings."
                      : "Choosing this preset applies one retrieval setup to every intent."}
                    />
                  </h2>
                  {active && <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-bold text-green-700">ACTIVE</span>}
                </div>
                <p className="mt-1 text-xs text-gray-600">{preset.description}</p>
                <button
                  type="button"
                  disabled={busy || active}
                  onClick={() => onPreset(preset.profile_name)}
                  className={`mt-3 rounded-lg px-3 py-1.5 text-xs font-bold ${active ? "bg-green-600 text-white" : "bg-gray-900 text-white"} disabled:opacity-100`}
                >
                  {active ? "In use" : "Use this preset"}
                </button>
              </div>
              );
            })}
          </div>
        )}

        {tab === "Multi-LLM" && (
          <div className="grid gap-3 md:grid-cols-2">
            {profiles.filter((profile) => profile.provider !== "gemini" && profile.provider !== "openai").map((profile) => {
              const ping = pings[profile.id];
              const active = activeLlm?.provider === profile.provider && activeLlm?.model === profile.model;
              return (
                <div key={profile.id} className="rounded-xl bg-white p-4 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="flex items-center gap-1 font-bold">
                      {profile.model}
                      <Hint text={`Context window ${profile.context_window || "n/a"}. Typical latency ${profile.latency || "n/a"}. These notes are not settings. Ping only measures reply time.`} />
                    </h2>
                    {active && <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-bold text-green-700">ACTIVE</span>}
                  </div>
                  <p className="mt-1 text-xs text-gray-600">{profile.fit || profile.description}</p>
                  <p className="mt-1 text-[11px]">
                    {ping?.status === "online" && `Online ${ping.latency_ms} ms`}
                    {ping?.status === "offline" && `Offline ${ping.message || ""}`}
                    {ping?.status === "checking" && "Checking..."}
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button type="button" onClick={() => onPing(profile)} className="rounded-lg border px-3 py-1.5 text-xs font-bold">Ping</button>
                    <button
                      type="button"
                      disabled={busy || active}
                      onClick={() => onSelectModel(profile)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-bold text-white ${active ? "bg-green-600" : "bg-gray-900"} disabled:opacity-100`}
                    >
                      {active ? "In use" : "Use this model"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {tab === "Benchmark" && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <div className="flex items-center gap-1 text-xs font-semibold">
                    <label htmlFor="benchmark-baseline">Baseline</label>
                    <Hint text="The preset the candidate is compared against." />
                  </div>
                  <select id="benchmark-baseline" className="mt-1 block rounded-lg border px-2 py-1.5" value={baselineName} onChange={(event) => setBaselineName(event.target.value)}>
                    {Object.keys(presets).map((name) => <option key={name}>{name}</option>)}
                  </select>
                </div>
                <div>
                  <div className="flex items-center gap-1 text-xs font-semibold">
                    <label htmlFor="benchmark-candidate">Candidate</label>
                    <Hint text="The preset you want to measure." />
                  </div>
                  <select id="benchmark-candidate" className="mt-1 block rounded-lg border px-2 py-1.5" value={candidateName} onChange={(event) => setCandidateName(event.target.value)}>
                    {Object.keys(presets).map((name) => <option key={name}>{name}</option>)}
                  </select>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    setError("");
                    try {
                      setBenchmark(await runBenchmark(baselineName, candidateName));
                    } catch (err) {
                      setError(err.message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                  className="rounded-lg bg-gray-900 px-3 py-2 text-xs font-bold text-white disabled:opacity-60"
                >
                  {busy ? "Running..." : "Run benchmark"}
                </button>
                <Hint text="Runs 2 questions from the spec set and compares whether the candidate finds the expected document and how fast it is." />
              </div>
              {benchmark && (
                <>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    <div className="rounded-lg bg-gray-50 p-3">
                      <div className="flex items-center gap-1 text-[11px] text-gray-500">Delta score <Hint text="Candidate hit score minus baseline. 100 means the expected source was found." /></div>
                      <div className="text-lg font-bold">{benchmark.summary.delta_score}</div>
                    </div>
                    <div className="rounded-lg bg-gray-50 p-3">
                      <div className="flex items-center gap-1 text-[11px] text-gray-500">Speedup <Hint text="Baseline time divided by candidate time. Above 1 means the candidate is faster." /></div>
                      <div className="text-lg font-bold">{benchmark.summary.speedup}x</div>
                    </div>
                    <div className="rounded-lg bg-gray-50 p-3">
                      <div className="flex items-center gap-1 text-[11px] text-gray-500">Cases <Hint text="How many spec questions ran. This button runs 2." /></div>
                      <div className="text-lg font-bold">{benchmark.summary.cases}</div>
                    </div>
                  </div>
                  {benchmark.details?.length > 0 && (
                    <div className="mt-3 overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b text-[11px] text-gray-500">
                            <th className="py-2 pr-3 font-semibold">Question</th>
                            <th className="py-2 pr-3 font-semibold">{baselineName} score</th>
                            <th className="py-2 pr-3 font-semibold">{candidateName} score</th>
                            <th className="py-2 pr-3 font-semibold">{baselineName} time</th>
                            <th className="py-2 pr-3 font-semibold">{candidateName} time</th>
                            <th className="py-2 font-semibold">Speedup</th>
                          </tr>
                        </thead>
                        <tbody>
                          {benchmark.details.map((row) => (
                            <tr key={row.id || row.query} className="border-t align-top">
                              <td className="py-2 pr-3">{row.query}</td>
                              <td className="py-2 pr-3">{row.baseline_score}</td>
                              <td className="py-2 pr-3">{row.candidate_score}</td>
                              <td className="py-2 pr-3">{row.baseline_seconds}s</td>
                              <td className="py-2 pr-3">{row.candidate_seconds}s</td>
                              <td className="py-2">{row.speedup}x</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {benchmark.llm_summary && (
                    <div className="mt-3 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-xs leading-5 text-gray-800">
                      <div className="mb-1 flex items-center gap-1 font-semibold text-gray-500">
                        Summary
                        <Hint text="Written by the active model from both answers, their sources, and the times in this table." />
                      </div>
                      {benchmark.llm_summary}
                    </div>
                  )}
                </>
              )}
            </div>
            <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50">
                  <tr>{["Score", "Level", "Content", "Citation"].map((head) => <th key={head} className="px-3 py-2">{head}</th>)}</tr>
                </thead>
                <tbody>
                  {RUBRIC.map((row) => (
                    <tr key={row[0]} className="border-t">{row.map((cell) => <td key={cell} className="px-3 py-2">{cell}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <h2 className="mb-2 flex items-center gap-1 font-bold">
                Spec questions
                <Hint text="These are the spec questions. Hover a row for what that case checks." />
              </h2>
              <ul className="space-y-2 text-xs">
                {CASES.map(([query, intent, note]) => (
                  <li key={query} className="flex items-center gap-1">
                    <span><span className="font-bold">{intent}</span> — {query}</span>
                    <Hint text={note} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </main>
      {toast && <div className="fixed right-4 top-4 rounded-xl bg-gray-900 px-4 py-3 text-xs font-bold text-white shadow-xl">{toast}</div>}
    </div>
  );
}
