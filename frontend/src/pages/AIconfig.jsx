import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LayoutDashboard, FolderClosed, MessageSquare, LogOut, Sliders } from "lucide-react";
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
const RUBRIC = [
  ["5", "สมบูรณ์แบบ", "ตอบครบและตัวเลขถูกต้อง", "อ้างอิงชื่อโครงงานหรือเลขหน้าชัด"],
  ["4", "ถูกต้องส่วนใหญ่", "สาระครบ อาจขาดรายละเอียดเล็กน้อย", "ไม่มีข้อมูลเท็จ"],
  ["3", "พอใช้", "ตอบได้บางส่วน", "ไม่ขัดแย้ง แต่ข้อมูลไม่พอ"],
  ["2", "ไม่ตรงประเด็น", "ดึงโครงงานที่ไม่เกี่ยว", "อ้างอิงผิดเล่ม"],
  ["1", "ล้มเหลว", "ตอบผิดหรือแต่งข้อมูล", "ภาพหลอนหรือระบบ error"],
];
const CASES = [
  ["อาจารสุรพลดูแลเรื่องไรบ้าง", "FACTUAL_LOOKUP", "LLM แก้คำผิดแล้วหาที่ปรึกษา"],
  ["โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง", "FACTUAL_LOOKUP", "BM25 ดึงชื่อฮาร์ดแวร์ตรง"],
  ["ขั้นตอนการทำงานและการทดลองของ The LoRaWAN", "DEEP_DIVE", "ตัดสารบัญแล้วจัดอันดับวิธีวิจัย"],
  ["ใครเป็นที่ปรึกษาของ The LoRaWAN", "FACTOID", "ตอบจาก metadata โดยไม่เรียก LLM"],
  ["The LoRaWAN เป็นระบบประเภทไหน", "EXPLANATION", "ใช้ประเภทโครงงานที่สกัดไว้"],
  ["โครงงาน The LoRaWAN มีการเชื่อมต่อกับ Line Notify หรือไม่", "FACTOID", "ปฏิเสธเมื่อเอกสารไม่มีข้อมูล"],
  ["เปรียบเทียบโครงงาน The LoRaWAN กับ BSLD ด้านจุดประสงค์และฮาร์ดแวร์", "COMPARISON", "แบ่งโควตาสองโครงงาน"],
  ["แล้วโครงงานนี้ใช้ฮาร์ดแวร์อะไรบ้าง", "DEEP_DIVE", "จำโครงงานจากคำถามก่อนหน้า"],
];

const numberFields = [
  ["top_k", "top_k"],
  ["rerank_top_n", "rerank_top_n"],
  ["min_score", "min_score"],
  ["max_context_chunks", "max_context_chunks"],
  ["max_chunks_per_project", "max_chunks_per_project"],
  ["max_total_projects", "max_total_projects"],
  ["temperature", "temperature"],
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
      notify(`บันทึก ${selected} แล้ว คำถามถัดไปจะใช้ค่านี้`);
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
      notify("คืนค่า Intent ตามสเปกแล้ว");
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
      notify(`สลับ preset เป็น ${name}`);
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
      notify(`คำถามถัดไปใช้ ${profile.model}`);
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
        <h1 className="text-xl font-bold">AI Configuration</h1>
        <p className="mb-4 text-xs text-gray-500">ค่าจากสเปกส่งมอบ บันทึกแล้วมีผลกับคำถามถัดไป</p>
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
                  <div className={`text-[11px] ${selected === key ? "text-indigo-100" : "text-gray-600"}`}>{intents[key]?.label_th}</div>
                </button>
              ))}
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <p className="mb-3 text-xs text-gray-500">{draft.description_th}</p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {numberFields.map(([field, label]) => (
                  <label key={field} className="text-xs font-semibold">
                    {label}
                    <input
                      className="mt-1 w-full rounded-lg border px-3 py-2 font-normal"
                      value={draft[field] ?? ""}
                      onChange={(event) => updateDraft(field, event.target.value)}
                    />
                  </label>
                ))}
              </div>
              <p className="mt-2 text-[11px] text-gray-500">max_chunks_per_project ช่วยไม่ให้โครงงานเดียวกินบริบทตอนเปรียบเทียบ</p>
              <div className="mt-3 flex flex-wrap gap-4 text-xs">
                {["enable_fast_path", "enable_hybrid", "enable_boilerplate_filter", "preserve_raw_code"].map((field) => (
                  <label key={field} className="flex items-center gap-2">
                    <input type="checkbox" checked={Boolean(draft[field])} onChange={(event) => updateDraft(field, event.target.checked)} />
                    {field}
                  </label>
                ))}
              </div>
              <label className="mt-3 block text-xs font-semibold">
                คำสั่งเพิ่มของ Intent นี้
                <textarea
                  rows={3}
                  placeholder="เช่น ตอบเป็นตาราง Markdown"
                  className="mt-1 w-full rounded-lg border px-3 py-2 font-normal"
                  value={draft.custom_system_instruction || ""}
                  onChange={(event) => updateDraft("custom_system_instruction", event.target.value)}
                />
              </label>
              <div className="mt-3 flex gap-2">
                <button type="button" disabled={busy} onClick={onSaveIntent} className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-60">
                  {busy ? "Saving..." : "Save Intent"}
                </button>
                <button type="button" disabled={busy} onClick={onReset} className="rounded-lg border px-4 py-2 text-xs font-bold">
                  Reset all
                </button>
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
                <div className="flex items-center justify-between">
                  <h2 className="font-bold">{preset.profile_name}</h2>
                  {active && <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-bold text-green-700">ACTIVE</span>}
                </div>
                <p className="mt-1 text-xs text-gray-600">{preset.description}</p>
                {active && <p className="mt-1 text-[11px] text-green-700">คำถามถัดไปใช้ top_k โควตา และตัวกรองของโหมดนี้</p>}
                <button
                  type="button"
                  disabled={busy || active}
                  onClick={() => onPreset(preset.profile_name)}
                  className={`mt-3 rounded-lg px-3 py-1.5 text-xs font-bold ${active ? "bg-green-600 text-white" : "bg-gray-900 text-white"} disabled:opacity-100`}
                >
                  {active ? "กำลังใช้งาน" : "สลับมาใช้โหมดนี้"}
                </button>
              </div>
              );
            })}
          </div>
        )}

        {tab === "Multi-LLM" && (
          <div className="grid gap-3 md:grid-cols-2">
            {profiles.map((profile) => {
              const ping = pings[profile.id];
              const active = activeLlm?.provider === profile.provider && activeLlm?.model === profile.model;
              return (
                <div key={profile.id} className="rounded-xl bg-white p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <h2 className="font-bold">{profile.model}</h2>
                    {active && <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-bold text-green-700">ACTIVE</span>}
                  </div>
                  <p className="mt-1 text-xs text-gray-600">{profile.fit || profile.description}</p>
                  <p className="mt-1 text-[11px] text-gray-500">{profile.context_window} · {profile.latency}</p>
                  <p className="mt-1 text-[11px]">
                    {ping?.status === "online" && `Online ${ping.latency_ms} ms`}
                    {ping?.status === "offline" && `Offline ${ping.message || ""}`}
                    {ping?.status === "checking" && "กำลังทดสอบ..."}
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button type="button" onClick={() => onPing(profile)} className="rounded-lg border px-3 py-1.5 text-xs font-bold">ทดสอบ Ping</button>
                    <button
                      type="button"
                      disabled={busy || active}
                      onClick={() => onSelectModel(profile)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-bold text-white ${active ? "bg-green-600" : "bg-gray-900"} disabled:opacity-100`}
                    >
                      {active ? "กำลังใช้งาน" : "เลือกใช้งาน"}
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
                <label className="text-xs font-semibold">
                  Baseline
                  <select className="mt-1 block rounded-lg border px-2 py-1.5" value={baselineName} onChange={(event) => setBaselineName(event.target.value)}>
                    {Object.keys(presets).map((name) => <option key={name}>{name}</option>)}
                  </select>
                </label>
                <label className="text-xs font-semibold">
                  Candidate
                  <select className="mt-1 block rounded-lg border px-2 py-1.5" value={candidateName} onChange={(event) => setCandidateName(event.target.value)}>
                    {Object.keys(presets).map((name) => <option key={name}>{name}</option>)}
                  </select>
                </label>
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
                  {busy ? "กำลังทดสอบ..." : "เริ่มการทดสอบ Benchmark"}
                </button>
              </div>
              <p className="mt-2 text-[11px] text-gray-500">รัน 2 ข้อจากชุดทดสอบในสเปก เทียบว่า candidate เจอเอกสารถูกกว่าและเร็วกว่า baseline แค่ไหน</p>
              {benchmark && (
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  <div className="rounded-lg bg-gray-50 p-3"><div className="text-[11px] text-gray-500">Delta score</div><div className="text-lg font-bold">{benchmark.summary.delta_score}</div></div>
                  <div className="rounded-lg bg-gray-50 p-3"><div className="text-[11px] text-gray-500">Speedup</div><div className="text-lg font-bold">{benchmark.summary.speedup}x</div></div>
                  <div className="rounded-lg bg-gray-50 p-3"><div className="text-[11px] text-gray-500">Cases</div><div className="text-lg font-bold">{benchmark.summary.cases}</div></div>
                </div>
              )}
            </div>
            <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50">
                  <tr>{["คะแนน", "ระดับ", "เนื้อหา", "การอ้างอิง"].map((head) => <th key={head} className="px-3 py-2">{head}</th>)}</tr>
                </thead>
                <tbody>
                  {RUBRIC.map((row) => (
                    <tr key={row[0]} className="border-t">{row.map((cell) => <td key={cell} className="px-3 py-2">{cell}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <h2 className="mb-2 font-bold">ชุดคำถามทดสอบ</h2>
              <ul className="space-y-2 text-xs">
                {CASES.map(([query, intent, note]) => (
                  <li key={query}><span className="font-bold">{intent}</span> — {query}<div className="text-gray-500">{note}</div></li>
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
