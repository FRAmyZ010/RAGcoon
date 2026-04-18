import json
import os
import requests
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct


#config
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama:latest")

QDRANT_URL = "https://2e97a8b5-3d34-4220-93e5-f3ec5a812dfc.eu-west-2-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6ZTU2ZmFjY2YtYmQyNy00MjMxLTgzM2ItZWVkZWRlNTAzMjlkIn0.DIkGKru01l4YRPGshAsqXOcOwXVQGkch6teKiDsPBiQ"
COLLECTION = "project_documents"

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    check_compatibility=False
)

#embedding and retrieval functions
def embed(text):
    res = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    #to check if embedding is successful
    data = res.json()
    if "embedding" in data:
        return data["embedding"]
    else:
        print("Embedding Error:", data)
        return [0.0] * 768 

def question_requires_project_answer(question):
    q = question.lower()
    if "project " in q:
        for name in ["project a", "project b", "project c", "project d", "project e", "project f", "project g", "project z"]:
            if name in q:
                return name
    return None


def get_llm_response(question, context_list):
    if not context_list:
        return "I don't know"

    project_name = question_requires_project_answer(question)
    context_text = "\n".join(context_list)
    if project_name and project_name not in context_text.lower():
        return "I don't know"

    prompt = f"""You are a strict knowledge extraction assistant.
Use only the context below to answer the question. Do not invent anything.
If the answer is not contained in the context, reply exactly: I don't know.

Context:
{context_text}
---
Question:
{question}
Answer:
"""

    res = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0
            }
        }
    )

    response = res.json().get("response", "").strip()
    if response.lower().startswith("question:") and "answer:" in response.lower():
        answer_index = response.lower().index("answer:") + len("answer:")
        response = response[answer_index:].strip()

    if "i don't know" in response.lower() or "not specified" in response.lower() or "cannot be answered" in response.lower():
        return "I don't know"

    return response

def retrieve_context(question):

    query_vector = embed(question)

    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=5  
    ).points


    contexts = []
    for r in results:
        text = r.payload.get("text", "")
        if text not in contexts:
            contexts.append(text)
    
    return contexts


#dummy data for testing
def insert_dummy():
    documents = [
        "Project A is a web application for dormitory search. It costs 10000 baht. Status: completed.",
        "Project B is a machine learning model for disease prediction. It costs 20000 baht. Status: in progress.",
        "Project C is a mobile app for food delivery. It costs 15000 baht. Status: completed.",
        "Project D is a chatbot system using RAG and LLM. It costs 25000 baht. Status: developing.",
        "Project E is a data analytics dashboard for business insights. It costs 30000 baht. Status: completed.",
        "Project A uses React and Node.js.",
        "Project B uses Python and scikit-learn.",
        "Project C uses Flutter.",
        "Project D uses Qdrant and Ollama.",
        "Project E uses Power BI and SQL.",
        "There are 5 projects in total.",
        "The most expensive project is Project E costing 30000 baht.",
        "The cheapest project is Project A costing 10000 baht."
    ]
    
    points = []
    for doc in documents:
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embed(doc),
                payload={"text": doc}
            )
        )

    client.upsert(collection_name=COLLECTION, points=points)
    print("--- Dummy data inserted successfully ---")


#main

if __name__ == "__main__":
    insert_dummy()
    print("RAG System Ready! (Type 'exit' to quit)") 
    while True:
        question = input("\nQuestion: ")
        if question.lower() == "exit":
            break
        #find context
        contexts = retrieve_context(question)   
        #use context to answer
        answer = get_llm_response(question, contexts)
        print("\n" + "="*30)
        print("Q:", question)
        print("A:", answer.strip())
        print("="*30)