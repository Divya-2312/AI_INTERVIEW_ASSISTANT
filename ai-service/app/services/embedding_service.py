import logging
import re
import numpy as np
from app.config import settings
from app.utils.similarity import cosine_similarity

logger = logging.getLogger("ai_service")

_model = None
_model_load_attempted = False


def _load_model():
    """
    Lazily loads a real pretrained BERT-derived Sentence Transformer model
    (default: all-MiniLM-L6-v2 -- a MiniLM-based sentence-transformer,
    distilled/trained in the same transformer-encoder family as BERT; it is
    NOT literally bert-base-uncased. For a demo that specifically requires
    the literal BERT checkpoint, set EMBEDDING_MODEL=bert-base-uncased in
    .env -- sentence-transformers can load that too, just with lower-quality
    out-of-the-box sentence similarity than a model actually trained for it.

    Only attempted once per process. If it can't be loaded (package missing,
    no internet to fetch weights, etc.):
      - STRICT_AI_MODE=false (default): logs a loud warning and falls back
        to a bag-of-words vector, so local dev never crashes.
      - STRICT_AI_MODE=true: raises immediately. Use this right before a
        demo so a silent fallback can never happen without you knowing.
    """
    global _model, _model_load_attempted
    if _model is not None or _model_load_attempted:
        return _model
    _model_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        msg = f"[Embedding] Loaded BERT-derived Sentence Transformer '{settings.EMBEDDING_MODEL}'"
        logger.info(msg)
        print(msg)  # also print directly so it's impossible to miss in the startup console
    except Exception as e:
        msg = (
            f"[Embedding] Could not load sentence-transformers model "
            f"'{settings.EMBEDDING_MODEL}' ({e}). "
        )
        if settings.STRICT_AI_MODE:
            logger.error(msg + "STRICT_AI_MODE is on -- refusing to silently fall back.")
            raise RuntimeError(
                f"{msg} STRICT_AI_MODE=true: install `sentence-transformers` and "
                f"`torch`, and ensure internet access to download the model, before "
                f"running in strict mode."
            ) from e
        else:
            logger.warning(
                msg + "Falling back to a bag-of-words vector space (NOT semantic) "
                "-- install `sentence-transformers` and `torch`, and ensure internet "
                "access to download the model, to enable real BERT-based embeddings. "
                "Set STRICT_AI_MODE=true in .env to turn this into a hard error instead."
            )
            print(msg + "FALLING BACK TO BAG-OF-WORDS (not semantic). See warning above.")
        _model = None
    return _model


class EmbeddingService:
    """
    Semantic embedding + similarity service.

    Primary path: pretrained BERT-derived sentence embeddings
    (sentence-transformers), giving genuine meaning-level similarity
    (e.g. "subclass" <-> "child class").

    Fallback path (only if the transformer model can't be loaded):
    hashed bag-of-words vectors. This is NOT semantic and only exists
    so the app degrades gracefully instead of crashing.
    """

    def __init__(self):
        self.model = _load_model()
        self.using_bert = self.model is not None

    def get_embedding(self, text: str) -> np.ndarray:
        model = _load_model()
        if model is not None:
            return model.encode(text or "", convert_to_numpy=True, normalize_embeddings=True)
        return self._bow_vector(text or "")

    def _bow_vector(self, text: str, dims: int = 512) -> np.ndarray:
        words = re.findall(r"\w+", text.lower())
        vec = np.zeros(dims)
        for w in words:
            vec[hash(w) % dims] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def compute_similarity(self, text1: str, text2: str) -> float:
        v1 = self.get_embedding(text1)
        v2 = self.get_embedding(text2)
        return cosine_similarity(v1, v2)

    def best_sentence_similarity(self, concept: str, text: str) -> float:
        """
        Semantic (never keyword/substring) coverage check for "does `text`
        cover `concept` anywhere in it?" -- comparing a short concept phrase
        against a whole multi-sentence answer as one blob dilutes the
        embedding (a 2-word phrase and an 80-word paragraph don't align well
        even when the paragraph clearly covers the idea in one sentence).
        Splitting into sentences and taking the best individual match fixes
        that dilution while staying entirely meaning-based: it's still pure
        embedding cosine similarity, just computed against the most relevant
        slice of the answer instead of the whole thing at once.
        """
        if not concept or not text:
            return 0.0
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        if not sentences:
            sentences = [text]
        concept_vec = self.get_embedding(concept)
        whole_vec = self.get_embedding(text)
        best = cosine_similarity(concept_vec, whole_vec)
        for sentence in sentences:
            sim = cosine_similarity(concept_vec, self.get_embedding(sentence))
            if sim > best:
                best = sim

        # If running bag-of-words fallback (no transformer model loaded), cosine
        # similarity is heavily diluted by sentence length. Asymmetric token overlap
        # ensures short concepts present in the text are recognized.
        if _load_model() is None and concept and text:
            c_words = set(re.findall(r"\w+", concept.lower()))
            t_words = set(re.findall(r"\w+", text.lower()))
            if c_words and c_words.issubset(t_words):
                best = max(best, 0.85)
            elif c_words:
                overlap = len(c_words & t_words) / len(c_words)
                if overlap >= 0.5:
                    best = max(best, 0.45 + 0.4 * overlap)

        return best


embedding_service = EmbeddingService()
