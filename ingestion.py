from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import hashlib, os, uuid, logging, httpx

QDRANT_COLLECTION_NAME = "Q1"
QDRANT_URL = "http://localhost:6333"
EMBEDDING_MODEL = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

try:
    client = QdrantClient(
        url=QDRANT_URL
    )
    QDRANT_INSTANCE = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=EMBEDDING_MODEL,
    )
except:
    client = QdrantClient(
        url=QDRANT_URL
    )
    client.create_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    QDRANT_INSTANCE = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=EMBEDDING_MODEL,
    )

async def ingestData(source_url:str) -> tuple[bool,str]:
    try:
        response = await fetch_url(source_url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        pdf_content = response.content
        document_hash = calculate_pdf_hash(pdf_content)
        logging.info(f"Calculated PDF hash: {document_hash}")
    except httpx.RequestError as e:
        logging.error(f"Failed to download PDF: {e}")
        return False, None

    # check if the document already exists in the VectorDB
    logging.info("Checking if the content already exists")
    if await check_for_existing_document(source_url, document_hash):
        return True,document_hash

    # create a temporary file to load the pdf from the binary
    logging.info("Attempting to load document")
    temp_file_path = f"temp_{uuid.uuid4()}.pdf"
    with open(temp_file_path, "wb") as f:
        f.write(pdf_content)
    loader = PyMuPDFLoader(temp_file_path)
    docs = loader.load()
    # add hash and source metadata
    for doc in docs:
        doc.metadata["content_hash"] = document_hash
        doc.metadata["source"] = source_url
    os.remove(temp_file_path)

    # check if docs is loading
    if not docs:
        logging.error("Document loading failed")
        return False,None

    # split the docs into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
    split_docs = text_splitter.split_documents(documents=docs)
    logging.info("Document chunking complete")

    try:
        await QDRANT_INSTANCE.aadd_documents(split_docs)
        logging.info("Chunks loaded in DB")
        return True,document_hash
    except Exception as e:
        logging.info(f"Chunk loading failed: {e}")
        return False,None
        
async def fetch_url(source_url:str):
    async with httpx.AsyncClient() as client:
        response = await client.get(source_url)
        response.raise_for_status()
        return response

def calculate_pdf_hash(pdf_content: bytes) -> str:
    return hashlib.sha256(pdf_content).hexdigest()

async def check_for_existing_document(document_source: str, document_hash: str) -> bool:
    try:
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
        search_results = await QDRANT_INSTANCE.asimilarity_search("dummy query", k=1, filter=qdrant_filter)
        if search_results:
            logging.info("Document with the same source and content hash already exists. Skipping ingestion")
            return True
        else:
            logging.info("Document not found. Proceeding with ingestion")
            return False

    except Exception as e:
        logging.info(f"Collection '{QDRANT_COLLECTION_NAME}' does not exist yet. Assuming no duplicates: {e}")
        return False