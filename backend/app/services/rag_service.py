from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.core.config import settings

# Vector data lives in InterviewIQ/chroma_db (ignored by Git)
CHROMA_DIR = str(Path(__file__).resolve().parents[3] / "chroma_db")


def _vector_store() -> Chroma:
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.gemini_api_key,
    )
    return Chroma(
        collection_name="job_descriptions",
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


def ingest_job_description(pdf_path: str, interview_id: int) -> int:
    """Load a JD PDF, split it, embed the chunks, and store them. Returns the chunk count."""
    pages = PyPDFLoader(pdf_path).load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(pages)
    chunks = [c for c in chunks if c.page_content.strip()]
    if not chunks:
        raise ValueError("No readable text found. The PDF may be a scanned image.")

    for chunk in chunks:
        chunk.metadata = {"interview_id": interview_id}

    store = _vector_store()
    old = store.get(where={"interview_id": interview_id})
    if old["ids"]:
        store.delete(ids=old["ids"])
    store.add_documents(chunks)
    return len(chunks)


def retrieve_context(interview_id: int, query: str, k: int = 4) -> list[str]:
    """Return the k chunks of this interview's JD most relevant to the query."""
    store = _vector_store()
    docs = store.similarity_search(query, k=k, filter={"interview_id": interview_id})
    return [d.page_content for d in docs]