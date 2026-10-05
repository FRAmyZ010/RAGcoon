const STORAGE_KEY = "ragcoon.chat.v1";
const TITLE_MAX = 40;
const MAX_TURNS = 3;
const STORAGE_BUDGET = 4_500_000;

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
  let remaining = threads.slice();
  while (remaining.length > 0) {
    const payload = JSON.stringify({
      threads: remaining.map((thread) => ({
        id: thread.id,
        title: thread.title,
        updatedAt: thread.updatedAt,
        messages: thread.messages,
      })),
    });
    if (payload.length > STORAGE_BUDGET) {
      remaining.pop();
      continue;
    }
    try {
      localStorage.setItem(STORAGE_KEY, payload);
      return remaining;
    } catch (error) {
      if (error?.name !== "QuotaExceededError") throw error;
      remaining.pop();
    }
  }
  localStorage.removeItem(STORAGE_KEY);
  return [];
}

export function upsertChatThread(threads, thread) {
  const next = [
    thread,
    ...threads.filter((item) => item.id !== thread.id),
  ].sort((a, b) => b.updatedAt - a.updatedAt);
  return saveChatThreads(next);
}

export function removeChatThread(threads, threadId) {
  const next = threads.filter((thread) => thread.id !== threadId);
  return saveChatThreads(next);
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
