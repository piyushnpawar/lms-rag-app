from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
import requests
import hashlib
import os
import uuid

QDRANT_COLLECTION_NAME = "Q1"
QDRANT_URL = "http://localhost:6333"

def ingestData(url:str):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        pdf_content = response.content
        document_hash = calculate_pdf_hash(pdf_content)
    except requests.exceptions.RequestException as e:
        print(f"Failed to download PDF: {e}")
        return False

    embedding_model = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    if check_for_existing_document(embedding_model,url, document_hash):
        return False

    temp_file_path = f"temp_{uuid.uuid4()}.pdf"
    with open(temp_file_path, "wb") as f:
        f.write(pdf_content)
    loader = PyMuPDFLoader(temp_file_path)
    docs = loader.load()
    for doc in docs:
        doc.metadata["content_hash"] = document_hash
        doc.metadata["source"] = url
    os.remove(temp_file_path)

    if not docs:
        print("Document loading failed. Exiting.")
        return False

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
    split_docs = text_splitter.split_documents(documents=docs)

    qdrant_instance = QdrantVectorStore.from_documents(
        documents = split_docs,
        embedding=embedding_model,
        url = QDRANT_URL,
        collection_name=QDRANT_COLLECTION_NAME,
        )

def calculate_pdf_hash(pdf_content: bytes) -> str:
    return hashlib.sha256(pdf_content).hexdigest()

def check_for_existing_document(embedding_model,document_source: str, document_hash: str):
    try:
        qdrant_instance = QdrantVectorStore.from_existing_collection(
            embedding=embedding_model,
            url=QDRANT_URL,
            collection_name=QDRANT_COLLECTION_NAME,
        )
        qdrant_filter = {
            "must": [
                {
                    "key": "metadata.source",
                    "match": {
                        "value": document_source
                    }
                },
                {
                    "key": "metadata.content_hash",
                    "match": {
                        "value": document_hash
                    }
                }
            ]
        }

        search_results = qdrant_instance.similarity_search("dummy query", k=1, filter=qdrant_filter)
        if search_results:
            print("--> Document with the same source and content hash already exists. Skipping ingestion.")
            return True
        else:
            print("--> Document not found. Proceeding with ingestion.")
            return False

    except Exception as e:
        print(f"Collection '{QDRANT_COLLECTION_NAME}' does not exist yet. Assuming no duplicates: {e}")
        return False