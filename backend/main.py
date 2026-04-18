from step1_context import answer_question


def format_context_preview(context: str, limit: int = 220) -> str:
    preview = " ".join(context.split())
    if len(preview) <= limit:
        return preview
    return f"{preview[:limit].rstrip()}..."


if __name__ == "__main__":
    print("Senior Project Document QA System")
    print("This system answers questions from the senior project document repository.")
    print("Type 'exit' to quit.")

    while True:
        question = input("\nQuestion: ").strip()

        if question.lower() == "exit":
            print("Leaving the Senior Project document repository system.")
            break

        if not question:
            print("Please enter a question.")
            continue

        contexts, answer = answer_question(question)

        print("Retrieved context:")
        for index, context in enumerate(contexts, 1):
            print(f"[{index}] {format_context_preview(context)}")

        print("Answer:")
        print(answer)
        print(f"Reference snippets used: {len(contexts)}")
