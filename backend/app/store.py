"""ChromaDB index management.

The collection name includes a hash of the knowledge-base file, so editing the
KB automatically builds a fresh index on the next start and removes the old one.
"""
import hashlib

import chromadb

from . import gemini
from .chunker import load_chunks
from .config import get_settings


def ensure_index(force: bool = False):
    s = get_settings()
    chunks = load_chunks(s.kb_path)
    fingerprint = hashlib.sha256(s.kb_path.read_bytes()).hexdigest()[:12]
    name = f"{s.collection_name}_{fingerprint}"

    client = chromadb.PersistentClient(path=str(s.chroma_dir))
    existing = [getattr(c, "name", c) for c in client.list_collections()]

    if name in existing and not force:
        collection = client.get_collection(name)
        if collection.count() == len(chunks):
            return collection

    for old in existing:
        if old.startswith(s.collection_name):
            client.delete_collection(old)

    collection = client.create_collection(name, metadata={"hnsw:space": "cosine"})
    vectors = gemini.embed([c.text for c in chunks], "RETRIEVAL_DOCUMENT")
    collection.add(
        ids=[c.id for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )
    return collection
