"""
Vivioo Memory — Vector Store (Step 5)
ChromaDB-backed vector storage and search.

ChromaDB is the MIRROR — entries/ JSON files are the source of truth.
If ChromaDB gets corrupted, rebuild from entries. Never the other way around.
"""

import os
import json
from typing import List, Dict, Optional

VECTORS_DIR = os.path.join(os.path.dirname(__file__), "vectors")
COLLECTION_NAME = "vivioo_memories"

# ChromaDB client — initialized lazily
_client = None
_collection = None


def init_store(persist_dir: str = None) -> bool:
    """
    Initialize the ChromaDB vector store.

    Args:
        persist_dir: directory for ChromaDB persistence (default: ./vectors/)

    Returns:
        True if initialized successfully, False if ChromaDB not available
    """
    global _client, _collection

    try:
        import chromadb
    except ImportError:
        return False

    persist = persist_dir or VECTORS_DIR
    os.makedirs(persist, exist_ok=True)

    _client = chromadb.PersistentClient(path=persist)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return True


def _get_collection():
    """Get the ChromaDB collection, initializing if needed."""
    global _collection
    if _collection is None:
        if not init_store():
            raise RuntimeError(
                "ChromaDB not available. Run: pip install chromadb"
            )
    return _collection


def add_entry(entry_id: str, embedding: List[float], metadata: dict,
              content: str) -> None:
    """
    Add an entry's embedding to the vector store.

    Args:
        entry_id: unique entry ID
        embedding: the embedding vector
        metadata: entry metadata (branch, tags, stored_at, etc.)
        content: the enriched text that was embedded
    """
    collection = _get_collection()

    # ChromaDB metadata must be flat strings/numbers/bools
    flat_meta = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            flat_meta[k] = v
        elif isinstance(v, list):
            flat_meta[k] = json.dumps(v)
        elif v is None:
            flat_meta[k] = ""

    collection.upsert(
        ids=[entry_id],
        embeddings=[embedding],
        metadatas=[flat_meta],
        documents=[content],
    )


def remove_entry(entry_id: str) -> None:
    """Remove an entry from the vector store."""
    collection = _get_collection()
    try:
        collection.delete(ids=[entry_id])
    except Exception:
        pass  # Entry might not exist


def search(query_embedding: List[float], top_k: int = 5,
           branch: str = None) -> List[dict]:
    """
    Search the vector store by embedding similarity.

    Args:
        query_embedding: the query's embedding vector
        top_k: number of results to return
        branch: if provided, filter to this branch only

    Returns:
        List of results, each with:
        {
            "id": entry_id,
            "score": similarity_score (0-1, higher = more similar),
            "content": the embedded text,
            "metadata": {branch, tags, stored_at, ...}
        }

        Sorted by score descending.
    """
    collection = _get_collection()

    where_filter = None
    if branch:
        where_filter = {"branch": branch}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    if not results or not results.get("ids") or not results["ids"][0]:
        return []

    output = []
    for i, entry_id in enumerate(results["ids"][0]):
        # ChromaDB returns distances (lower = closer for cosine)
        # Convert to similarity score (higher = more similar)
        distance = results["distances"][0][i] if results.get("distances") else 0
        score = 1 - distance  # cosine distance → cosine similarity

        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
        # Restore lists from JSON strings
        for k, v in metadata.items():
            if isinstance(v, str) and v.startswith("["):
                try:
                    metadata[k] = json.loads(v)
                except json.JSONDecodeError:
                    pass

        output.append({
            "id": entry_id,
            "score": round(score, 4),
            "content": results["documents"][0][i] if results.get("documents") else "",
            "metadata": metadata,
        })

    # Sort by score descending
    output.sort(key=lambda x: x["score"], reverse=True)
    return output


def search_by_branch_summary(query_embedding: List[float],
                              branch_summaries: Dict[str, List[float]]) -> List[dict]:
    """
    Compare a query embedding against branch summary embeddings.
    Used for routing — finding which branch a query belongs to.

    Args:
        query_embedding: the query's embedding vector
        branch_summaries: {branch_path: summary_embedding}

    Returns:
        List of {branch, score} sorted by score descending
    """
    results = []
    for branch_path, summary_emb in branch_summaries.items():
        if summary_emb is None:
            continue
        score = _cosine_similarity(query_embedding, summary_emb)
        results.append({"branch": branch_path, "score": round(score, 4)})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_entry_count() -> int:
    """Get the total number of entries in the vector store."""
    try:
        collection = _get_collection()
        return collection.count()
    except Exception:
        return 0


def rebuild_from_entries(entries: List[dict], embed_fn) -> int:
    """
    Rebuild the entire vector store from entry data.

    Args:
        entries: list of entry dicts (each with id, branch, content, etc.)
        embed_fn: function that takes text and returns embedding vector

    Returns:
        Number of entries added
    """
    from entry_manager import get_enriched_text

    collection = _get_collection()
    # Clear existing
    try:
        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)
    except Exception:
        pass

    count = 0
    for entry in entries:
        enriched = get_enriched_text(entry)
        embedding = embed_fn(enriched)
        if embedding is None:
            continue

        metadata = {
            "branch": entry.get("branch", ""),
            "stored_at": entry.get("stored_at", ""),
            "happened_at": entry.get("happened_at", ""),
            "tags": json.dumps(entry.get("tags", [])),
            "_outdated": entry.get("_outdated", False),
        }

        add_entry(entry["id"], embedding, metadata, enriched)
        count += 1

    return count


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
