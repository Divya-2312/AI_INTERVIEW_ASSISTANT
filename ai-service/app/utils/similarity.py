import numpy as np
from scipy.spatial.distance import cosine
import re

def compute_tf_vector(text: str, vocabulary: list) -> np.ndarray:
    words = re.findall(r'\w+', text.lower())
    vec = np.zeros(len(vocabulary))
    for i, word in enumerate(vocabulary):
        vec[i] = words.count(word)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))
