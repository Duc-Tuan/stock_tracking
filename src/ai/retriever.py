import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

def load_documents(data_path="src/ai/data"):
    docs = []
    for file in os.listdir(data_path):
        if file.endswith(".txt") or file.endswith(".md"):
            with open(os.path.join(data_path, file), "r", encoding="utf-8") as f:
                content = f.read()
                docs.append(Document(page_content=content, metadata={"source": file}))
    return docs

def build_vector_db(data_path="src/ai/data", db_path="src/ai/vector_db"):
    docs = load_documents(data_path)
    print(f"📄 Loaded {len(docs)} documents")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(db_path)
    print("✅ Vector database created!")

if __name__ == "__main__":
    build_vector_db()
