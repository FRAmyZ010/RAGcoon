import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CircleHelp, LayoutDashboard, FolderClosed, MessageSquare, LogOut, Sliders } from "lucide-react";
import ConfirmModal from "../components/ui/ConfirmModal";
import { clearAuth } from "../services/authApi";
import {
  applyPreset,
  saveNamedPreset,
  rankQuality,
  fetchIntents,
  runBenchmark,
  fetchLlms,
  fetchRag,
  deleteNamedPreset,
  resetIntents,
} from "../services/aiConfigApi";

function Hint({ text }) {
  if (!text) return null;
  return (
    <span className="group relative inline-flex">
      <button type="button" className="rounded-full text-gray-400 hover:text-gray-700" aria-label={text}>
        <CircleHelp className="h-4 w-4" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-30 mb-1.5 hidden w-72 rounded-lg bg-gray-900 px-3 py-2 text-left text-sm font-normal leading-snug text-white shadow-lg group-hover:block group-focus-within:block"
      >
        {text}
      </span>
    </span>
  );
}

const TABS = ["Configuration", "Presets", "Benchmark"];

const MODEL_CHOICES = [
  { model: "llama3.2:3b", tone: "Balanced", emoji: "🥇", blurb: "Best mix of speed and a correct answer." },
  { model: "qwen2.5:3b", tone: "Fast", emoji: "🥈", blurb: "Highest speed on this machine." },
  { model: "gemma3:4b", tone: "Academic", emoji: "🥉", blurb: "Strongest academic writing and tables." },
];

function showFact(value) {
  if (value === true) return "On";
  if (value === false) return "Off";
  return value === undefined || value === null || value === "" ? "—" : String(value);
}

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
const INTENT_EMOJI = {
  FACTOID: "📌",
  FACTUAL_LOOKUP: "🔎",
  DEEP_DIVE: "🔬",
  EXPLANATION: "💡",
  COMPARISON: "⚖️",
  RECOMMENDATION: "✨",
  EXPLORATORY: "🗺️",
  CODE: "💻",
};

const PRESET_TONE = {
  Balanced: "border-emerald-200 bg-emerald-50/60",
  Fast: "border-amber-200 bg-amber-50/70",
  Academic: "border-indigo-200 bg-indigo-50/70",
};
const PRESET_EMOJI = {
  Balanced: "⚖️",
  Fast: "⚡",
  Academic: "🎓",
};
const DETAIL_ROWS = [
  ["llm_model", "Model"],
  ["top_k", "Top K"],
  ["rerank_top_n", "Rerank"],
  ["max_context_chunks", "Context"],
  ["max_chunks_per_project", "Per project"],
  ["temperature", "Temperature"],
  ["prompt_preset", "Prompt"],
];
const DETAIL_SWITCHES = [
  ["enable_hybrid", "Hybrid"],
  ["enable_reranker", "Reranker"],
  ["enable_boilerplate_filter", "Filter"],
  ["enable_fast_path", "Fast path"],
];

function PresetCard({ preset, active, open, busy, onUse, onToggle, onEdit, onDelete, showIntents = false }) {
  const tone = PRESET_TONE[preset.title] || "border-gray-200 bg-white";
  const emoji = PRESET_EMOJI[preset.title] || preset.emoji;
  const rows = DETAIL_ROWS.filter(([key]) => preset[key] !== undefined && preset[key] !== null && preset[key] !== "");
  const switches = DETAIL_SWITCHES.filter(([key]) => preset[key] === true || preset[key] === false);
  const onSwitches = switches.filter(([key]) => preset[key] === true).map(([, label]) => label);
  const offSwitches = switches.filter(([key]) => preset[key] === false).map(([, label]) => label);
  return (
    <article className={`self-start rounded-xl border p-4 ${active ? "border-emerald-500 bg-white ring-2 ring-emerald-100" : tone}`}>
      <div className={`flex flex-col justify-between ${onEdit ? "h-[13.5rem]" : "h-[11.5rem]"}`}>
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white text-2xl shadow-sm" aria-hidden="true">{emoji}</span>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-base font-bold leading-6">{preset.title}</h3>
            <p className="truncate text-sm text-gray-500">{preset.llm_model || "Saved settings"}</p>
          </div>
        </div>
        <p className="line-clamp-2 min-h-10 text-sm leading-5 text-gray-600" title={preset.blurb}>{preset.blurb}</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || active}
            onClick={() => onUse(preset.profile_name)}
            className={`rounded-lg px-3 py-1.5 text-sm font-bold ${active ? "bg-emerald-600 text-white" : "bg-gray-900 text-white"} disabled:opacity-100`}
          >
            {active ? "In use" : "Use"}
          </button>
          <button
            type="button"
            onClick={() => onToggle(open ? "" : preset.profile_name)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-bold"
          >
            {open ? "Hide" : "Details"}
          </button>
          {onEdit && (
            <button type="button" disabled={busy} onClick={() => onEdit(preset)} className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-bold">
              Edit
            </button>
          )}
          {onDelete && (
            <button type="button" disabled={busy} onClick={() => onDelete(preset)} className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-sm font-bold text-red-700">
              Delete
            </button>
          )}
        </div>
      </div>
      {open && (
        <dl className="mt-3 space-y-1.5 border-t border-black/5 pt-3 text-sm">
          {rows.map(([key, label]) => (
            <div key={key} className="flex items-center justify-between gap-3">
              <dt className="text-gray-500">{label}</dt>
              <dd className="truncate font-semibold text-gray-900">{showFact(preset[key])}</dd>
            </div>
          ))}
          {onSwitches.length > 0 && (
            <div className="flex items-start justify-between gap-3">
              <dt className="text-gray-500">On</dt>
              <dd className="text-right font-semibold text-gray-900">{onSwitches.join(", ")}</dd>
            </div>
          )}
          {offSwitches.length > 0 && (
            <div className="flex items-start justify-between gap-3">
              <dt className="text-gray-500">Off</dt>
              <dd className="text-right font-semibold text-gray-900">{offSwitches.join(", ")}</dd>
            </div>
          )}
          {showIntents && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-gray-500">Intents</dt>
              <dd className="font-semibold text-gray-900">{Object.keys(preset.intents || {}).length} saved</dd>
            </div>
          )}
        </dl>
      )}
    </article>
  );
}

function CompareCard({ preset, open, onToggle }) {
  const title = preset.title || preset.profile_name;
  const tone = PRESET_TONE[title] || "border-gray-200 bg-white";
  const emoji = PRESET_EMOJI[title] || preset.emoji || "🏷️";
  const blurb = preset.blurb || "";
  const rows = DETAIL_ROWS.filter(([key]) => preset[key] !== undefined && preset[key] !== null && preset[key] !== "");
  const switches = DETAIL_SWITCHES.filter(([key]) => preset[key] === true || preset[key] === false);
  const onSwitches = switches.filter(([key]) => preset[key] === true).map(([, label]) => label);
  const offSwitches = switches.filter(([key]) => preset[key] === false).map(([, label]) => label);
  return (
    <article className={`self-start rounded-xl border p-4 ${tone}`}>
      <div className="flex h-[11.5rem] flex-col justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white text-2xl shadow-sm" aria-hidden="true">{emoji}</span>
          <div className="min-w-0">
            <h3 className="truncate text-base font-bold leading-6">{title}</h3>
            <p className="truncate text-sm text-gray-500">{preset.llm_model || "Saved settings"}</p>
          </div>
        </div>
        <p className="line-clamp-2 min-h-10 text-sm leading-5 text-gray-600" title={blurb}>{blurb}</p>
        <button type="button" onClick={() => onToggle(open ? "" : preset.profile_name)} className="w-fit rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-bold">
          {open ? "Hide" : "Details"}
        </button>
      </div>
      {open && (
      <dl className="mt-3 space-y-1.5 border-t border-black/5 pt-3 text-sm">
        {rows.map(([key, label]) => (
          <div key={key} className="flex items-center justify-between gap-3">
            <dt className="text-gray-500">{label}</dt>
            <dd className="truncate font-semibold text-gray-900">{showFact(preset[key])}</dd>
          </div>
        ))}
        {onSwitches.length > 0 && (
          <div className="flex items-start justify-between gap-3">
            <dt className="text-gray-500">On</dt>
            <dd className="text-right font-semibold text-gray-900">{onSwitches.join(", ")}</dd>
          </div>
        )}
        {offSwitches.length > 0 && (
          <div className="flex items-start justify-between gap-3">
            <dt className="text-gray-500">Off</dt>
            <dd className="text-right font-semibold text-gray-900">{offSwitches.join(", ")}</dd>
          </div>
        )}
        {preset.kind === "intent_bundle" && (
          <div className="flex items-center justify-between gap-3">
            <dt className="text-gray-500">Intents</dt>
            <dd className="font-semibold text-gray-900">{Object.keys(preset.intents || {}).length} saved</dd>
          </div>
        )}
      </dl>
      )}
    </article>
  );
}

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
  const [showcase, setShowcase] = useState([]);
  const [activePreset, setActivePreset] = useState("");
  const [profiles, setProfiles] = useState([]);
  const [activeLlm, setActiveLlm] = useState(null);
  const [chosenModel, setChosenModel] = useState(null);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [baselineName, setBaselineName] = useState("winner_rank1_llama3_2_3b");
  const [candidateName, setCandidateName] = useState("winner_rank2_qwen2_5_3b");
  const [benchmark, setBenchmark] = useState(null);
  const [quality, setQuality] = useState(null);
  const [presetName, setPresetName] = useState("");
  const [askName, setAskName] = useState(false);
  const [openPreset, setOpenPreset] = useState("");
  const [openQuestion, setOpenQuestion] = useState("");
  const [openCompare, setOpenCompare] = useState("");
  const [openRank, setOpenRank] = useState("");
  const [confirmState, setConfirmState] = useState(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

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
        setShowcase(data.showcase_presets || []);
        setActivePreset(data.active_preset || data.active_config?.profile_name || "");
      })
      .catch(() => {});
    fetchLlms()
      .then((data) => {
        setProfiles(data.profiles || []);
        setActiveLlm(data.active || null);
        setChosenModel(data.active || null);
      })
      .catch(() => {});
  }, []);

  const chooseIntent = (key) => {
    const next = { ...intents, [selected]: { ...(intents[selected] || {}), ...draft } };
    setIntents(next);
    setSelected(key);
    setDraft(next[key] ? { ...next[key] } : null);
  };

  const updateDraft = (field, value) => setDraft((current) => ({ ...current, [field]: value }));

  const onSavePreset = async () => {
    const name = presetName.trim();
    if (!name) {
      setAskName(true);
      setError("Name this preset before saving.");
      return;
    }
    const model = chosenModel || activeLlm;
    if (!model?.model) {
      setError("Select a model before saving a preset.");
      return;
    }
    const nextIntents = { ...intents, [selected]: { ...(intents[selected] || {}), ...draft } };
    setBusy(true);
    setError("");
    try {
      const data = await saveNamedPreset({
        profile_name: name,
        llm_provider: model.provider || "ollama",
        llm_model: model.model,
        preview_intent: selected,
        intents: nextIntents,
      });
      setIntents(nextIntents);
      setActivePreset(data.active_preset);
      const refreshed = await fetchRag();
      setPresets(refreshed.available_presets || {});
      setShowcase(refreshed.showcase_presets || []);
      setAskName(false);
      setActiveLlm(model);
      setTab("Presets");
      setOpenPreset(data.active_preset);
      notify(`Saved ${data.active_preset}. It is under Custom. Chat uses these settings and ${model.model}.`);
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
      if (data.kind === "intent_bundle") {
        const fresh = await fetchIntents();
        setIntents(fresh.intents || {});
        setDraft(fresh.intents?.[selected] || null);
        const models = await fetchLlms();
        setActiveLlm(models.active || null);
        setChosenModel(models.active || null);
      }
      notify(`Switched the active preset to ${name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onEditPreset = (preset) => {
    const nextIntents = preset.intents;
    if (nextIntents && Object.keys(nextIntents).length) {
      const key = nextIntents[preset.preview_intent] ? preset.preview_intent : Object.keys(nextIntents)[0];
      setIntents(nextIntents);
      setSelected(key);
      setDraft({ ...nextIntents[key] });
    }
    if (preset.llm_model) {
      setChosenModel({ provider: preset.llm_provider || "ollama", model: preset.llm_model });
    }
    setPresetName(preset.profile_name || "");
    setAskName(true);
    setTab("Configuration");
  };

  const deletePreset = async (preset) => {
    setBusy(true);
    setError("");
    try {
      await deleteNamedPreset(preset.profile_name);
      const refreshed = await fetchRag();
      setPresets(refreshed.available_presets || {});
      setShowcase(refreshed.showcase_presets || []);
      setActivePreset(refreshed.active_preset || "");
      if (openPreset === preset.profile_name) setOpenPreset("");
      notify(`Deleted ${preset.profile_name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onDeletePreset = (preset) => {
    setConfirmState({
      title: "Delete preset",
      message: `Delete ${preset.profile_name}?`,
      confirmLabel: "Delete",
      run: () => deletePreset(preset),
    });
  };

  const acceptConfirm = async () => {
    const run = confirmState?.run;
    if (!run) return;
    setConfirmBusy(true);
    try {
      await run();
      setConfirmState(null);
    } finally {
      setConfirmBusy(false);
    }
  };

  const onSelectModel = (profile) => {
    setChosenModel({ provider: profile.provider, model: profile.model });
  };

  const showcaseNames = new Set(showcase.map((preset) => preset.profile_name));
  const customPresets = Object.values(presets).filter(
    (preset) => (preset.kind === "intent_bundle" || preset.custom) && !showcaseNames.has(preset.profile_name),
  );
  const compareChoices = [
    ...showcase.map((preset) => ({
      name: preset.profile_name,
      title: preset.title || preset.profile_name,
      preset,
    })),
    ...customPresets.map((preset) => ({
      name: preset.profile_name,
      title: preset.profile_name,
      preset: {
        ...preset,
        title: preset.profile_name,
        emoji: "🏷️",
        blurb: `Saved by you. Answers with ${preset.llm_model || "the selected model"}.`,
      },
    })),
  ];
  const compareTitle = (name) => compareChoices.find((choice) => choice.name === name)?.title || name;

  useEffect(() => {
    const names = compareChoices.map((choice) => choice.name).filter(Boolean);
    if (!names.length) return;
    setBaselineName((current) => (names.includes(current) ? current : names[0]));
    setCandidateName((current) => (names.includes(current) ? current : names[1] || names[0]));
  }, [showcase, presets]);

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

      <main className="min-w-0 flex-1 overflow-y-auto p-6">
        <h1 className="mb-5 flex items-center gap-2 text-2xl font-bold">
          AI Configuration
          <Hint text="A built-in preset applies one retrieval setup to every question. A saved preset stores every intent on this page plus the selected model." />
        </h1>
        <div className="mb-5 flex flex-wrap gap-2">
          {TABS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={`rounded-full px-4 py-2 text-sm font-semibold ${tab === item ? "bg-gray-900 text-white" : "bg-white text-gray-700"}`}
            >
              {item}
            </button>
          ))}
        </div>
        {error && <p className="mb-3 text-sm font-semibold text-red-700">{error}</p>}

        {tab === "Configuration" && draft && (
          <div className="space-y-5">
            <section>
              <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-gray-500">Model</h2>
              <div className="grid items-start gap-3 md:grid-cols-3">
                {MODEL_CHOICES.map((choice) => {
                  const profile = profiles.find((item) => item.model === choice.model) || { provider: "ollama", model: choice.model };
                  const active = (chosenModel?.model || activeLlm?.model) === choice.model;
                  const tone = PRESET_TONE[choice.tone] || "border-gray-200 bg-white";
                  return (
                    <button
                      key={choice.model}
                      type="button"
                      onClick={() => onSelectModel(profile)}
                      className={`flex h-20 items-center gap-3 rounded-xl border px-4 py-3 text-left ${active ? "border-emerald-500 bg-white ring-2 ring-emerald-100" : tone}`}
                    >
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white text-2xl shadow-sm" aria-hidden="true">{choice.emoji}</span>
                      <span className="min-w-0">
                        <span className="block truncate text-base font-bold leading-6">{choice.model}</span>
                        <span className="line-clamp-2 text-sm text-gray-500">{choice.blurb}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
            <section>
              <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-gray-500">Intent</h2>
              <div className="flex flex-wrap gap-2">
                {INTENT_ORDER.map((key) => {
                  const active = selected === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => chooseIntent(key)}
                      className={`inline-flex h-10 items-center gap-2 rounded-full border px-3.5 text-sm font-semibold ${active ? "border-emerald-500 bg-white ring-2 ring-emerald-100" : "border-gray-200 bg-white text-gray-700"}`}
                    >
                      <span aria-hidden="true">{INTENT_EMOJI[key]}</span>
                      {INTENT_COPY[key]?.[0]}
                    </button>
                  );
                })}
              </div>
            </section>
            <section className="rounded-xl border border-gray-200 bg-white p-4">
              <h2 className="mb-3 flex items-center gap-1.5 text-sm font-bold uppercase tracking-wide text-gray-500">
                {INTENT_COPY[selected]?.[0]}
                <Hint text={INTENT_COPY[selected]?.[1]} />
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {NUMBER_FIELDS.map(([field, label, hint]) => (
                  <div key={field}>
                    <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-500">
                      <label htmlFor={`intent-${field}`}>{label}</label>
                      <Hint text={hint} />
                    </div>
                    <input
                      id={`intent-${field}`}
                      className="mt-1 w-full rounded-lg border px-3 py-2 text-sm font-normal"
                      value={draft[field] ?? ""}
                      onChange={(event) => updateDraft(field, event.target.value)}
                    />
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {TOGGLES.map(([field, label, hint]) => {
                  const on = Boolean(draft[field]);
                  return (
                    <button
                      key={field}
                      type="button"
                      title={hint}
                      onClick={() => updateDraft(field, !on)}
                      className={`rounded-full px-3.5 py-1.5 text-sm font-semibold ${on ? "bg-gray-900 text-white" : "border border-gray-200 bg-gray-50 text-gray-600"}`}
                    >
                      {label}{on ? " on" : " off"}
                    </button>
                  );
                })}
              </div>
              <div className="mt-4">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-500">
                  <label htmlFor="intent-instruction">Extra instruction</label>
                  <Hint text="Appended to the system prompt for this intent only." />
                </div>
                <input
                  id="intent-instruction"
                  placeholder="Example: answer in a Markdown table"
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm font-normal"
                  value={draft.custom_system_instruction || ""}
                  onChange={(event) => updateDraft("custom_system_instruction", event.target.value)}
                />
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {askName && (
                  <input
                    autoFocus
                    value={presetName}
                    onChange={(event) => setPresetName(event.target.value)}
                    placeholder="Preset name"
                    className="w-52 rounded-lg border bg-white px-3 py-2 text-sm"
                  />
                )}
                <button type="button" disabled={busy} onClick={() => (askName ? onSavePreset() : setAskName(true))} className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-60">
                  {busy ? "Saving..." : askName ? "Save this name" : "Save preset"}
                </button>
                <button type="button" disabled={busy} onClick={onReset} className="rounded-lg border bg-white px-4 py-2 text-sm font-bold">
                  Reset
                </button>
              </div>
            </section>
          </div>
        )}

        {tab === "Presets" && (
          <div className="space-y-6">
            <section>
              <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-gray-500">Recommended</h2>
              <div className="grid items-start gap-4 md:grid-cols-3">
                {showcase.map((preset) => (
                  <PresetCard
                    key={preset.profile_name}
                    preset={preset}
                    active={activePreset === preset.profile_name}
                    open={openPreset === preset.profile_name}
                    busy={busy}
                    onUse={onPreset}
                    onToggle={setOpenPreset}
                  />
                ))}
              </div>
            </section>
            <section>
              <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-gray-500">Custom</h2>
              {customPresets.length === 0 ? (
                <p className="text-sm text-gray-500">No custom presets yet. Save one from Configuration.</p>
              ) : (
                <div className="grid items-start gap-4 md:grid-cols-3">
                  {customPresets.map((preset) => (
                    <PresetCard
                      key={preset.profile_name}
                      preset={{
                        ...preset,
                        emoji: "🏷️",
                        title: preset.profile_name,
                        blurb: `Saved by you. Answers with ${preset.llm_model || "the selected model"}.`,
                      }}
                      active={activePreset === preset.profile_name}
                      open={openPreset === preset.profile_name}
                      busy={busy}
                      onUse={onPreset}
                      onToggle={setOpenPreset}
                      onEdit={onEditPreset}
                      onDelete={onDeletePreset}
                      showIntents={preset.kind === "intent_bundle"}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {tab === "Benchmark" && (
          <div className="space-y-5">
            <section className="rounded-xl border border-gray-200 bg-white p-4">
              <h2 className="mb-3 flex items-center gap-1.5 text-sm font-bold uppercase tracking-wide text-gray-500">
                Compare
                <Hint text="Each preset answers the same questions 5 times. Score is the average chance of citing the expected document. Rank prefers the closer answer, then the faster one." />
              </h2>
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-500">
                    <label htmlFor="benchmark-baseline">Baseline</label>
                    <Hint text="The preset the candidate is compared against." />
                  </div>
                  <select id="benchmark-baseline" className="mt-1 block h-10 rounded-lg border bg-white px-3 text-sm" value={baselineName} onChange={(event) => setBaselineName(event.target.value)}>
                    {compareChoices.map((choice) => <option key={choice.name} value={choice.name}>{choice.title}</option>)}
                  </select>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-500">
                    <label htmlFor="benchmark-candidate">Candidate</label>
                    <Hint text="The preset you want to measure." />
                  </div>
                  <select id="benchmark-candidate" className="mt-1 block h-10 rounded-lg border bg-white px-3 text-sm" value={candidateName} onChange={(event) => setCandidateName(event.target.value)}>
                    {compareChoices.map((choice) => <option key={choice.name} value={choice.name}>{choice.title}</option>)}
                  </select>
                </div>
                <button
                  type="button"
                  disabled={busy || baselineName === candidateName}
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
                  className="h-10 rounded-lg bg-gray-900 px-4 text-sm font-bold text-white disabled:opacity-60"
                >
                  {busy ? "Running 5 times..." : "Compare · 5 runs"}
                </button>
                <button
                  type="button"
                  disabled={busy || showcase.length < 2}
                  onClick={async () => {
                    setBusy(true);
                    setError("");
                    try {
                      setQuality(await rankQuality(showcase.map((preset) => preset.profile_name)));
                    } catch (err) {
                      setError(err.message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                  className="h-10 rounded-lg border bg-white px-4 text-sm font-bold disabled:opacity-60"
                >
                  Rank recommended
                </button>
                <Hint text="Runs Balanced, Fast, and Academic on the same questions, five times each. Orders them by how often the expected document is cited, then by speed. It does not change the preset in use." />
              </div>
              <div className="mt-4 grid items-start gap-4 md:grid-cols-2">
                {[baselineName, candidateName].map((name) => {
                  const choice = compareChoices.find((item) => item.name === name);
                  return choice ? (
                    <CompareCard
                      key={name}
                      preset={choice.preset}
                      open={openCompare === name}
                      onToggle={setOpenCompare}
                    />
                  ) : null;
                })}
              </div>
              {benchmark && (
                <>
                  <div className="mt-4 flex flex-wrap gap-2 text-sm">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 font-semibold text-gray-700">
                      Delta {benchmark.summary.delta_score}
                      <Hint text="Candidate hit score minus baseline. 100 means the expected source was found." />
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 font-semibold text-gray-700">
                      {benchmark.summary.speedup}x
                      <Hint text="Baseline time divided by candidate time. Above 1 means the candidate is faster." />
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 font-semibold text-gray-700">
                      {benchmark.summary.cases} cases
                      <Hint text="How many spec questions ran. Each one is answered 5 times and the numbers here are the average." />
                    </span>
                  </div>
                  {benchmark.details?.length > 0 && (
                    <div className="mt-4 overflow-x-auto rounded-xl border border-gray-200">
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="border-b bg-gray-50 text-gray-500">
                            <th className="px-3 py-2.5 font-semibold">Question</th>
                            <th className="px-3 py-2.5 font-semibold">{compareTitle(baselineName)} score</th>
                            <th className="px-3 py-2.5 font-semibold">{compareTitle(candidateName)} score</th>
                            <th className="px-3 py-2.5 font-semibold">{compareTitle(baselineName)} time</th>
                            <th className="px-3 py-2.5 font-semibold">{compareTitle(candidateName)} time</th>
                            <th className="px-3 py-2.5 font-semibold">Speedup</th>
                          </tr>
                        </thead>
                        <tbody>
                          {benchmark.details.map((row) => (
                            <tr key={row.id || row.query} className="border-t align-top">
                              <td className="px-3 py-2.5">
                                <button type="button" className="text-left font-semibold text-gray-900 underline" onClick={() => setOpenQuestion((current) => (current === row.query ? "" : row.query))}>
                                  {row.query}
                                </button>
                                {openQuestion === row.query && (
                                  <div className="mt-1.5 space-y-1.5 font-normal text-gray-700">
                                    <p><span className="font-semibold">{compareTitle(baselineName)}:</span> {row.baseline_answer || "—"}</p>
                                    <p className="text-gray-500">Sources: {row.baseline_sources || "none"}</p>
                                    <p><span className="font-semibold">{compareTitle(candidateName)}:</span> {row.candidate_answer || "—"}</p>
                                    <p className="text-gray-500">Sources: {row.candidate_sources || "none"}</p>
                                  </div>
                                )}
                              </td>
                              <td className="px-3 py-2.5 font-semibold">{row.baseline_score}</td>
                              <td className="px-3 py-2.5 font-semibold">{row.candidate_score}</td>
                              <td className="px-3 py-2.5">{row.baseline_seconds}s</td>
                              <td className="px-3 py-2.5">{row.candidate_seconds}s</td>
                              <td className="px-3 py-2.5">{row.speedup}x</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {benchmark.llm_summary && (
                    <div className="mt-4 whitespace-pre-wrap rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-800">
                      <div className="mb-1 flex items-center gap-1 font-semibold uppercase tracking-wide text-gray-500">
                        Summary
                        <Hint text="Written by the active model from both answers, their sources, and the times in this table." />
                      </div>
                      {benchmark.llm_summary}
                    </div>
                  )}
                </>
              )}
            </section>
            {quality && (
              <section className="space-y-2">
                <h2 className="text-sm font-bold uppercase tracking-wide text-gray-500">
                  Closest answer first · average of {quality.repeats} runs
                </h2>
                {quality.presets.map((item, index) => {
                  const title = compareTitle(item.profile_name);
                  const tone = PRESET_TONE[title] || "border-gray-200 bg-white";
                  const emoji = PRESET_EMOJI[title] || compareChoices.find((choice) => choice.name === item.profile_name)?.preset.emoji || "🏷️";
                  return (
                    <article key={item.profile_name} className={`self-start rounded-xl border px-4 py-3 ${tone}`}>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white text-2xl shadow-sm" aria-hidden="true">{emoji}</span>
                        <div className="min-w-0 flex-1">
                          <div className="text-base font-bold leading-6">{index + 1}. {title}</div>
                          <div className="truncate text-sm text-gray-500">{item.llm_model}</div>
                        </div>
                        <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-gray-700">hit {item.score}</span>
                        <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-gray-700">{item.seconds}s</span>
                        <button type="button" onClick={() => setOpenRank((current) => (current === item.profile_name ? "" : item.profile_name))} className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-bold">
                          {openRank === item.profile_name ? "Hide" : "Details"}
                        </button>
                      </div>
                      {openRank === item.profile_name && (
                        <ul className="mt-3 space-y-1.5 border-t border-black/5 pt-3 text-sm text-gray-600">
                          {item.questions.map((question) => (
                            <li key={question.query} className="flex items-start justify-between gap-3">
                              <span className="min-w-0">{question.query}</span>
                              <span className="shrink-0 font-semibold text-gray-900">{question.score}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </article>
                  );
                })}
              </section>
            )}
            <section className="rounded-xl border border-gray-200 bg-white px-4 py-3">
              <h2 className="mb-2 flex items-center gap-1.5 text-sm font-bold uppercase tracking-wide text-gray-500">
                Spec questions
                <Hint text="These are the spec questions. Hover a row for what that case checks." />
              </h2>
              <ul className="grid gap-x-6 md:grid-cols-2">
                {CASES.map(([query, intent, note]) => (
                  <li key={query} className="flex items-start gap-2 border-b border-gray-100 py-2.5 text-sm leading-5 last:border-0 md:[&:nth-last-child(-n+2)]:border-0">
                    <span className="w-40 shrink-0 font-semibold text-gray-500">
                      <span aria-hidden="true">{INTENT_EMOJI[intent]} </span>{INTENT_COPY[intent]?.[0] || intent}
                    </span>
                    <span className="min-w-0 flex-1 text-gray-800">{query}</span>
                    <Hint text={note} />
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}
      </main>
      <ConfirmModal
        open={Boolean(confirmState)}
        title={confirmState?.title}
        message={confirmState?.message}
        confirmLabel={confirmState?.confirmLabel || "Delete"}
        danger
        busy={confirmBusy}
        onConfirm={acceptConfirm}
        onClose={() => { if (!confirmBusy) setConfirmState(null); }}
      />
      {toast && <div className="fixed right-4 top-4 z-[60] rounded-xl bg-gray-900 px-4 py-3 text-sm font-bold text-white shadow-xl">{toast}</div>}
    </div>
  );
}
