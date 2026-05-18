import shutil
from pathlib import Path

import lancedb
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore, create_kv_docstore
from langchain_community.vectorstores import LanceDB as LanceDBStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings

PARENT_CHUNK_SIZE = 1500
PARENT_CHUNK_OVERLAP = 100
CHILD_CHUNK_SIZE = 200
CHILD_CHUNK_OVERLAP = 20
PARENT_DOCSTORE_PATH = "./db/parent_docs"


def build_parent_retriever(
    embeddings: HuggingFaceEmbeddings, *, overwrite: bool = False
) -> ParentDocumentRetriever:
    db = lancedb.connect(settings.LANCEDB_PATH)
    docstore_path = Path(PARENT_DOCSTORE_PATH)

    if overwrite:
        if settings.TABLE_NAME in db.table_names():
            db.drop_table(settings.TABLE_NAME)
        if docstore_path.exists():
            shutil.rmtree(docstore_path)

    docstore_path.mkdir(parents=True, exist_ok=True)

    vectorstore = LanceDBStore(
        connection=db,
        embedding=embeddings,
        table_name=settings.TABLE_NAME,
    )
    docstore = create_kv_docstore(LocalFileStore(str(docstore_path)))

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK_SIZE, chunk_overlap=PARENT_CHUNK_OVERLAP
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_SIZE, chunk_overlap=CHILD_CHUNK_OVERLAP
    )

    return ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=docstore,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
