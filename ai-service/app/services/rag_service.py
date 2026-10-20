import os
import glob
import logging
import numpy as np
from app.services.embedding_service import embedding_service
from app.utils.similarity import cosine_similarity
from app.config import settings

logger = logging.getLogger("ai_service")


class RAGService:
    """
    Retrieval-Augmented Generation (RAG) Service.

    Loads curated subject knowledge (java/dbms/hr markdown files), splits
    it into chunks, and pre-computes a BERT embedding for each chunk once
    at startup. Retrieval at query time embeds the query and ranks chunks
    by cosine similarity in that semantic vector space -- not literal word
    overlap.
    """

    def __init__(self, knowledge_base_dir: str = None):
        if knowledge_base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            knowledge_base_dir = os.path.join(base_dir, "knowledge")

        self.knowledge_dir = knowledge_base_dir
        self.chunks = []
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        self.chunks = []
        md_files = glob.glob(os.path.join(self.knowledge_dir, "**", "*.md"), recursive=True)
        for filepath in md_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                    sections = text.split("\n#")
                    for sec in sections:
                        if sec.strip():
                            chunk_text = ("#" + sec).strip()
                            rel = os.path.relpath(filepath, self.knowledge_dir)
                            parts = rel.split(os.sep)
                            subject = parts[0] if len(parts) > 1 else "general"
                            self.chunks.append({
                                "subject": subject.lower(),
                                "filepath": rel,
                                "content": chunk_text,
                            })
            except Exception as e:
                logger.warning(f"[RAG] Warning loading {filepath}: {e}")

        # Pre-compute BERT embeddings once at load time so query-time
        # retrieval only has to embed the (short) query, not the whole KB.
        for chunk in self.chunks:
            chunk["embedding"] = embedding_service.get_embedding(chunk["content"])

        logger.info(
            f"[RAG] Loaded {len(self.chunks)} knowledge chunks "
            f"(semantic mode: {'BERT' if embedding_service.using_bert else 'bag-of-words fallback'})"
        )

    def retrieve_context(self, subject: str, query: str, top_k: int = 2, rotate: int = 0) -> list:
        """
        `rotate` (typically the number of questions already asked this
        session) shifts which window of matching chunks gets returned.
        Without this, a near-static `query` (e.g. "technical medium" -- see
        question_generator.py) would retrieve the exact same top chunk on
        every call for the same subject/difficulty, feeding the same
        knowledge-base content into every question prompt for the whole
        session regardless of what the actual question ends up being about.
        Rotating the window means later questions in a session pull
        different (still subject-matched, still ranked by relevance)
        material instead of all converging on chunk #1.
        """
        norm_subject = (subject or "general").lower()
        relevant_chunks = [c for c in self.chunks if c["subject"] == norm_subject or norm_subject in c["subject"]]
        if not relevant_chunks:
            relevant_chunks = self.chunks
        if not relevant_chunks:
            return []

        query_vec = embedding_service.get_embedding(query)

        scored = []
        for chunk in relevant_chunks:
            sim = cosine_similarity(query_vec, chunk["embedding"])
            scored.append((sim, chunk["content"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return []
        start = (rotate * top_k) % len(scored)
        window = (scored[start:] + scored[:start])[:top_k]
        return [item[1] for item in window]


rag_service = RAGService()
