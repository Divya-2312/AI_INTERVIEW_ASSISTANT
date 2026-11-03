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


SYNONYM_MAP = {
    # Relational DBMS synonyms
    "table": ["relation", "entity"],
    "relation": ["table", "entity"],
    "row": ["tuple", "record"],
    "tuple": ["row", "record"],
    "record": ["row", "tuple"],
    "column": ["attribute", "field"],
    "attribute": ["column", "field"],
    "field": ["column", "attribute", "member variable", "property"],
    "primary key": ["candidate key", "unique identifier", "pk"],
    "candidate key": ["primary key", "minimal superkey"],
    "foreign key": ["referential integrity", "fk"],
    "cardinality": ["number of rows", "number of tuples", "row count"],
    "degree": ["number of columns", "number of attributes", "column count"],
    "atomicity": ["all or nothing", "atomic transaction"],
    "isolation": ["concurrency control", "serializability"],
    "durability": ["persistence", "non-volatile storage"],
    "consistency": ["integrity constraints", "valid state"],
    # Java & OOP synonyms
    "method": ["function", "member function"],
    "function": ["method", "procedure"],
    "subclass": ["child class", "derived class"],
    "child class": ["subclass", "derived class"],
    "derived class": ["subclass", "child class"],
    "superclass": ["parent class", "base class"],
    "parent class": ["superclass", "base class"],
    "base class": ["superclass", "parent class"],
    "instantiation": ["instance creation", "object creation"],
    "instance creation": ["instantiation", "object creation"],
    "inheritance": ["extends", "subclassing", "derived class"],
    "encapsulation": ["data hiding", "information hiding"],
    "polymorphism": ["method overriding", "dynamic dispatch", "runtime polymorphism"],
    "overriding": ["runtime polymorphism", "dynamic dispatch"],
    "overloading": ["compile-time polymorphism", "static polymorphism"],
    "garbage collection": ["automatic memory management", "gc"],
}


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
        if not hasattr(self, "_cache"):
            self._cache = {}
        cleaned = (text or "").strip()
        if cleaned in self._cache:
            return self._cache[cleaned]
        model = _load_model()
        if model is not None:
            vec = model.encode(cleaned, convert_to_numpy=True, normalize_embeddings=True)
        else:
            vec = self._bow_vector(cleaned)
        if len(self._cache) < 5000:
            self._cache[cleaned] = vec
        return vec

    def compute_similarity(self, text1: str, text2: str) -> float:
        v1 = self.get_embedding(text1)
        v2 = self.get_embedding(text2)
        return cosine_similarity(v1, v2)

    def is_similar_to_any(self, text: str, target_texts: list, threshold: float = 0.88) -> tuple:
        """
        Checks if `text` has Sentence-BERT cosine similarity >= `threshold` (default 0.88)
        against any string in `target_texts`, or matches after whitespace/case normalization.
        Returns (is_similar: bool, max_similarity: float, matching_target: str).
        """
        if not text or not target_texts:
            return False, 0.0, None

        norm_cand = re.sub(r"\s+", " ", str(text).lower().strip())
        for t in target_texts:
            if not t:
                continue
            norm_t = re.sub(r"\s+", " ", str(t).lower().strip())
            if norm_cand and norm_cand == norm_t:
                return True, 1.0, str(t)

        cand_vec = self.get_embedding(text)
        if cand_vec is None or len(cand_vec) == 0:
            return False, 0.0, None

        best_sim = 0.0
        best_match = None
        for t in target_texts:
            if not t:
                continue
            t_vec = self.get_embedding(str(t))
            sim = float(cosine_similarity(cand_vec, t_vec))
            if sim > best_sim:
                best_sim = sim
                best_match = str(t)
            if sim >= threshold:
                return True, sim, str(t)

        return best_sim >= threshold, best_sim, best_match

    def best_sentence_similarity(self, concept: str, text: str) -> float:
        """
        Semantic coverage check for "does `text` cover `concept` anywhere in it?"
        Splits into sentences and takes the best individual match with synonym support.
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

        # Check domain synonym expansions
        c_lower = concept.lower().strip()
        synonyms = SYNONYM_MAP.get(c_lower, [])
        for syn in synonyms:
            syn_vec = self.get_embedding(syn)
            for sentence in sentences:
                sim = cosine_similarity(syn_vec, self.get_embedding(sentence))
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

