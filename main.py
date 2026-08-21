import os
from dotenv import load_dotenv
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions
import re
import numpy as np
from src.split_thai import split_thai
import sys
from rank_bm25 import BM25Okapi
from pythainlp.tokenize import word_tokenize




load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_key,model_name="text-embedding-3-small"
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR = os.path.join(BASE_DIR, "data")


chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_persistent_storage"))
collection_name = "document_qa_collection"
collection = chroma_client.get_or_create_collection(
    name=collection_name, embedding_function=openai_ef
)

client = OpenAI(api_key=openai_key)

def load_documents_from_directory(directory_path):
    print("==== Loading documents from directory ====")
    documents = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            with open(
                os.path.join(directory_path, filename), "r", encoding="utf-8"
            ) as file:
                documents.append({"id": filename, "text": file.read()})
    return documents

# directory_path = "./data"
directory_path = os.path.join(os.path.dirname(__file__), "data")

documents = load_documents_from_directory(directory_path)

def get_openai_embedding(text,idx = None):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    embedding = response.data[0].embedding
    if idx is not None and idx % 100 == 0 :print("==== Generating embeddings... ====")
    return embedding
def build_index(directory_path=directory_path):

    chunked_documents = []
    for doc in documents:
        chunks = split_thai(doc["text"])
        print("==== Splitting docs into chunks ====")
        for i, chunk in enumerate(chunks):
            chunked_documents.append({"id": f"{doc['id']}_chunk{i+1}", "text": chunk})

    for idx,doc in enumerate(chunked_documents):
        if idx % 100 == 0 :print("==== Generating embeddings... ====")
        doc["embedding"] = get_openai_embedding(doc["text"])


    for idx,doc in enumerate(chunked_documents):
        if idx % 100 == 0 :print("==== Inserting chunks into db;;; ====")
        collection.upsert(
            ids=[doc["id"]], documents=[doc["text"]], embeddings=[doc["embedding"]]
        )


_data      = collection.get()
all_ids    = _data["ids"]
all_chunks = _data["documents"]
bm25 = BM25Okapi([word_tokenize(c, engine="newmm") for c in all_chunks])


def query_bm25(question, n_results=10):
    scores = bm25.get_scores(word_tokenize(question, engine="newmm"))
    top = sorted(range(len(scores)), key=lambda i: -scores[i])[:n_results]
    return [all_chunks[i] for i in top]


def query_documents(question, n_results=10):
    # query_embedding = get_openai_embedding(question)
    results = collection.query(query_texts=question, n_results=n_results)
    docs = results["documents"][0]      # [0] = first (only) query
    dists = results["distances"][0]


    for dist, text in zip(dists, docs):
        print(f"dist={dist:.3f} | {text[:200]}...")
    relevant_chunks = [doc for sublist in results["documents"] for doc in sublist]
    print("==== Returning relevant chunks ====")
    return relevant_chunks


def generate_response(question, relevant_chunks):
    context = "\n\n".join(relevant_chunks)
    prompt = (
        "You are an assistant for question-answering tasks. Use the following pieces of "
        "retrieved context to answer the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the answer concise."
        "\n\nContext:\n" + context + "\n\nQuestion:\n" + question +"ตอบจากข้อความที่ให้มาเท่านั้น ห้ามใช้ความรู้ภายนอกถ้าข้อความมีข้อมูลที่ตอบคำถามได้ ให้ตอบ แม้ถ้อยคำในคำถามกับในข้อความจะไม่ตรงกันทุกคำตอบว่า \"ไม่ทราบ\" เฉพาะเมื่อข้อความที่ให้มาไม่มีข้อมูลนั้นจริง ๆ"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        temperature=0,
    )

    answer = response.choices[0].message.content
    return answer

Retriever_Vec = True
n_results = 10



def main():
    if len(sys.argv) < 2:
        print('Usage:\n  python main.py index\n  python main.py ask "your question"')
        return
 
    command = sys.argv[1]
 
    if command == "index":
        build_index()
 
    elif command == "ask":
        if len(sys.argv) < 3:
            print('Usage: python main.py ask "your question"')
            return
        question = sys.argv[2]
        # chunks = query_documents(question)
        if Retriever_Vec:
            chunks = query_documents(question, n_results=n_results)
        else:
            chunks = query_bm25(question, n_results=n_results)
        print("\n" + generate_response(question, chunks))
 
    else:
        print(f"Unknown command: {command}")
 
 
if __name__ == "__main__":
    main()
 



# question = "สงครามโลกเกิดได้อย่างไร"
# relevant_chunks = query_documents(question)
# answer = generate_response(question, relevant_chunks)

# print(answer.content)