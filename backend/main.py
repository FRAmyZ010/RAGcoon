from step1_context import retrieve_context, get_llm_response, clean_answer

if __name__ == "__main__":
    question = input("Question: ")
    contexts = retrieve_context(question)
    answer = get_llm_response(question, contexts)
    print("\nAnswer:", answer)

