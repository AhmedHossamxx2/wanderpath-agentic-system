"""
Wanderpath Travel Agency - Vector Store Architecture
====================================================
Wraps ChromaDB to provide HNSW-indexed vector search with metadata payload
storage and pre-search metadata filtering capabilities.
"""

import os
import pathlib
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings


class WanderpathVectorStore:
    """
    Vector store manager using ChromaDB with persistent HNSW index,
    payload storage, and metadata index filtering.
    """

    def __init__(self, collection_name: str = "wanderpath_knowledge", persist_dir: str = "./rag/chroma_db"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)

        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Get or create collection with default embedding function
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Explicit HNSW Cosine Index
        )

    def ingest_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Ingests chunked documents with metadata payloads into the vector store."""
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def similarity_search(
        self, query_text: str, n_results: int = 3, metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs ANN similarity search with optional pre-filtering on metadata indices.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=metadata_filter  # Pre-search metadata index filter
        )

        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })

        return formatted_results