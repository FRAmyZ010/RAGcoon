import sys
from pathlib import Path
from typing import Any, cast

# HELLO

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent

for path in (str(PROJECT_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from retrieval import answer_question
from retrieval.performance import format_performance_summary


def print_divider(char="=", length=50):
    print(char * length)


def print_section(title: str):
    print_divider("-")
    print(title)
    print_divider("-")


if __name__ == "__main__":
    session_total_times: list[float] = []

    print_divider("=")
    print("📚 Senior Project Document QA System")
    print("Answer questions from the senior project document repository")
    print("Type 'exit' to quit")
    print_divider("=")

    while True:
        question = input("\n🔎 Question: ").strip()

        if question.lower() == "exit":
            print("\n👋 Exiting system...")

            if session_total_times:
                print_divider("=")
                print(format_performance_summary(
                    "Questions processed",
                    session_total_times
                ))

            break

        if not question:
            print("⚠️ Please enter a question.")
            continue

        result = cast(dict[str, Any], answer_question(question))

        timing = cast(dict[str, float], result["timing"])
        session_total_times.append(timing["total_seconds"])

        # ===================== RESULT =====================
        print("📌 RESULT")
        print_divider("=")

        print(f"🔹 Normalized Query: {result['normalized_query']}\n")

        print("💡 Answer:")
        print(f"{result['answer']}\n")

        contexts = cast(list[str], result["contexts"])
        sources = cast(list[str], result["sources"])
        print(f"📄 Reference snippets used: {len(contexts)}")

        for source in sources:
            print(f"Source: {source}")

        # ===================== TIMING =====================
        print_section("⏱️ Timing")

        print(f"Retrieval : {timing['retrieval_seconds']:.3f}s")
        print(f"Rerank    : {timing['rerank_seconds']:.3f}s")
        print(f"LLM       : {timing['llm_seconds']:.3f}s")
        print(f"Total     : {timing['total_seconds']:.3f}s")

        # ===================== WARNINGS =====================
        errors = cast(list[str], result["errors"])
        if errors:
            print_section("⚠️ Retrieval Warnings")

            for error in errors:
                print(f"- {error}")

        print_divider("=")
