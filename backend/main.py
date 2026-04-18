from performance import format_performance_summary
from step1_context import answer_question


def format_context_preview(context: str, limit: int = 220) -> str:
    preview = " ".join(context.split())
    return preview if len(preview) <= limit else f"{preview[:limit].rstrip()}..."


def print_divider(char="=", length=50):
    print(char * length)


def print_section(title: str):
    print_divider("-")
    print(f"{title}")
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
                print(format_performance_summary("Questions processed", session_total_times))
            print_divider("=")
            break

        if not question:
            print("⚠️ Please enter a question.")
            continue

        result = answer_question(question)
        timing = result["timing"]
        session_total_times.append(timing["total_seconds"])

        # ===================== RESULT =====================
        print_divider("=")
        print("📌 RESULT")
        print_divider("=")

        print(f"🔹 Normalized Query: {result['normalized_query']}\n")

        print("💡 Answer:")
        print(f"{result['answer']}\n")

        print(f"📄 Reference snippets used: {len(result['contexts'])}")

        # ===================== TIMING =====================
        print_section("⏱️ Timing")
        print(f"Retrieval : {timing['retrieval_seconds']:.3f}s")
        print(f"Rerank    : {timing['rerank_seconds']:.3f}s")
        print(f"LLM       : {timing['llm_seconds']:.3f}s")
        print(f"Total     : {timing['total_seconds']:.3f}s")

        # ===================== WARNINGS =====================
        if result["errors"]:
            print_section("⚠️ Retrieval Warnings")
            for error in result["errors"]:
                print(f"- {error}")

        # ===================== CONTEXT =====================
        print_section("📚 Retrieved Context")

        if result["scored_contexts"]:
            for i, item in enumerate(result["scored_contexts"], 1):
                print(f"[{i}] ⭐ Score: {item['score']:.4f}")
                print(f"     {format_context_preview(item['text'])}\n")
        else:
            print("- No context retrieved")

        print_divider("=")