"""Short-circuit chats that should not hit retrieval."""
import re

_GREETING = re.compile(
    r"^(สวัสดี(?:ครับ|ค่ะ|จ้า)?|ดีจ้า|ดีครับ|ดีค่ะ|hello|hi|hey|หวัดดี)[!?.\s]*$",
    re.IGNORECASE,
)
_SMALL_TALK = (
    "ทำอะไรได้บ้าง",
    "คุณคือใคร",
    "กินข้าวหรือยัง",
    "who are you",
    "what can you do",
)
_OUT_OF_DOMAIN = (
    "ผัดไทย",
    "สภาพอากาศ",
    "แต่งกลอน",
    "weather",
    "recipe",
)
_AMBIGUOUS = (
    "อันนั้น",
    "ข้อมูลเพิ่มเติม",
    "that one",
    "more detail",
    "more information",
)
_PROJECT_HINT = re.compile(
    r"โครงงาน|โปรเจค|โปรเจกต์|project|petfeeder|prefeeder|plc|ปี",
    re.IGNORECASE,
)


def prescreen_reply(question: str) -> str | None:
    text = (question or "").strip()
    if not text:
        return "I didn't catch a question. Ask me about a senior project whenever you're ready."
    compact = re.sub(r"\s+", "", text)
    if not re.search(r"[A-Za-zก-๙0-9]", compact) or re.fullmatch(r"[a-z]{8,}", compact, re.IGNORECASE):
        return "I couldn't understand that. Please ask again about a senior project."
    if _GREETING.fullmatch(text):
        return "Hello, I'm RAGcoon. I can help you look up Computer Engineering senior projects."
    lowered = text.casefold()
    if any(phrase in lowered for phrase in _SMALL_TALK) and not _PROJECT_HINT.search(text):
        return "I'm an assistant for the Computer Engineering senior-project archive. Ask about a project title, year, or advisor."
    if any(phrase in lowered for phrase in _OUT_OF_DOMAIN) and not _PROJECT_HINT.search(text):
        return "I can only answer questions about the senior projects in this archive."
    if any(phrase in lowered for phrase in _AMBIGUOUS) and not _PROJECT_HINT.search(text):
        return "Which project do you mean? A title or topic would help."
    return None
