"""Build (or rebuild) the vector index.   Usage: python -m scripts.ingest [--force]"""
import sys

from app.store import ensure_index

if __name__ == "__main__":
    collection = ensure_index(force="--force" in sys.argv)
    print(f"Index ready with {collection.count()} chunks ({collection.name}).")
