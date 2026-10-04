const STORAGE_KEY = "ragcoon.chat.v1";
const TITLE_MAX = 40;
const MAX_TURNS = 3;

function isMessage(value) {
  return (
    value &&
    (value.role === "user" || value.role === "bot") &&
    typeof value.text === "string"
  );
}

function isThread(value) {
  return (
    value &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    Array.isArray(value.messages) &&
    value.messages.every(isMessage)
  );
}

export function threadTitleFromMessages(messages) {
  const first = messages.find((message) => message.role === "user" && message.text.trim());
  const text = first?.text.trim() || "New chat";
  if (text.length <= TITLE_MAX) return text;
  return `${text.slice(0, TITLE_MAX)}…`;
}

export function loadChatThreads() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.threads)) {
      throw new Error("corrupt chat history");
    }
    return parsed.threads
      .filter(isThread)
      .map((thread) => ({
        ...thread,
        updatedAt: Number(thread.updatedAt) || 0,
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

export function saveChatThreads(threads) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      threads: threads.map((thread) => ({
        id: thread.id,
        title: thread.title,
        updatedAt: thread.updatedAt,
        messages: thread.messages,
      })),
    })
  );
}

export function upsertChatThread(threads, thread) {
  const next = [
    thread,
    ...threads.filter((item) => item.id !== thread.id),
  ].sort((a, b) => b.updatedAt - a.updatedAt);
  saveChatThreads(next);
  return next;
}

export function removeChatThread(threads, threadId) {
  const next = threads.filter((thread) => thread.id !== threadId);
  saveChatThreads(next);
  return next;
}

/** Prior turns only. UI role `bot` is sent as `assistant`. */
export function toApiMessages(messages, maxTurns = MAX_TURNS) {
  const turns = [];
  for (let index = 0; index < messages.length; index += 1) {
    const current = messages[index];
    const next = messages[index + 1];
    if (current?.role !== "user" || !current.text?.trim()) continue;
    if (next?.role !== "bot" || !next.text?.trim()) continue;
    turns.push(
      { role: "user", content: current.text },
      { role: "assistant", content: next.text }
    );
    index += 1;
  }
  return turns.slice(-maxTurns * 2);
}
