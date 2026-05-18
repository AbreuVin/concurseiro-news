from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from src.config import settings
from src.etl.doe_ba import scrape_doe
from src.rag.retriever import build_parent_retriever

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def _publications_to_documents(publications: list[dict]) -> list[Document]:
    return [
        Document(
            page_content=pub["content"],
            metadata={
                "materia_id": pub.get("materia_id", ""),
                "title": pub["title"],
                "date": pub["date"],
                "source": pub["source_url"],
            },
        )
        for pub in publications
    ]


def build_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def run_pipeline(days: int = 30) -> int:
    """Scrapa e indexa publicacoes do DOE-BA com hierarquia de chunks. Retorna n documentos."""
    print("[Pipeline] Iniciando ETL...")
    publications = scrape_doe(days=days)

    if not publications:
        print("[Pipeline] Nenhuma publicacao encontrada.")
        return 0

    docs = _publications_to_documents(publications)
    print(f"[Pipeline] {len(docs)} documentos obtidos.")

    print(f"[Pipeline] Carregando modelo de embedding '{EMBEDDING_MODEL}'...")
    embeddings = build_embeddings()

    print("[Pipeline] Indexando com hierarquia parent/child chunks...")
    retriever = build_parent_retriever(embeddings, overwrite=True)
    retriever.add_documents(docs)

    print(f"[Pipeline] {len(docs)} documentos indexados.")
    return len(docs)


if __name__ == "__main__":
    run_pipeline(days=30)
