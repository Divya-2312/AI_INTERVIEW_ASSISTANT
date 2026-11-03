import json
import os
import sys
import numpy as np

# Ensure ai-service is in sys.path
sys.path.insert(0, os.path.abspath("ai-service"))

from app.services.embedding_service import embedding_service


def find_near_duplicates_in_catalogue(filepath, subject_name, threshold=0.88):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Checking {len(items)} questions in {subject_name} catalogue...")
    texts = [item.get("questionText", "").strip() for item in items]
    
    # Batch encode with sentence-transformers
    model = embedding_service.model
    if model is not None:
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        # Cosine similarity matrix
        sim_matrix = np.dot(embeddings, embeddings.T)
    else:
        # Fallback to compute_similarity pairwise
        embeddings = np.array([embedding_service.get_embedding(t) for t in texts])
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = embeddings / norms
        sim_matrix = np.dot(normalized, normalized.T)

    pairs = []
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim >= threshold:
                pairs.append({
                    "subject": subject_name,
                    "similarity": sim,
                    "q1": items[i],
                    "q2": items[j]
                })

    pairs.sort(key=lambda x: x["similarity"], reverse=True)
    return pairs


def main():
    java_cat = "ai-service/app/data/question_bank/java_theory_catalogue.json"
    dbms_cat = "ai-service/app/data/question_bank/dbms_theory_catalogue.json"
    out_file = "verification_runs/catalogue_near_duplicates.txt"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    java_pairs = find_near_duplicates_in_catalogue(java_cat, "Java", threshold=0.88)
    dbms_pairs = find_near_duplicates_in_catalogue(dbms_cat, "DBMS", threshold=0.88)

    lines = []
    lines.append("================================================================================")
    lines.append("       MOCKMATE AI: CATALOGUE NEAR-DUPLICATE AUDIT (Cosine Similarity >= 0.88)")
    lines.append("================================================================================\n")
    lines.append(f"Model: {embedding_service.model.__class__.__name__ if embedding_service.model else 'BagOfWords'}")
    lines.append(f"Threshold: 0.88 cosine similarity (Sentence-BERT all-MiniLM-L6-v2)\n")

    lines.append(f"--- Java Theory Catalogue ({len(java_pairs)} near-duplicate pairs found) ---")
    if not java_pairs:
        lines.append("No pairs found with cosine similarity >= 0.88.\n")
    for idx, p in enumerate(java_pairs, 1):
        q1 = p["q1"]
        q2 = p["q2"]
        lines.append(f"Pair #{idx} | Cosine Similarity: {p['similarity']:.4f}")
        lines.append(f"  [Q1] ID: {q1.get('id')} ({q1.get('difficulty')}, {q1.get('category')}): {q1.get('questionText')}")
        lines.append(f"  [Q2] ID: {q2.get('id')} ({q2.get('difficulty')}, {q2.get('category')}): {q2.get('questionText')}")
        lines.append("")

    lines.append(f"\n--- DBMS Theory Catalogue ({len(dbms_pairs)} near-duplicate pairs found) ---")
    if not dbms_pairs:
        lines.append("No pairs found with cosine similarity >= 0.88.\n")
    for idx, p in enumerate(dbms_pairs, 1):
        q1 = p["q1"]
        q2 = p["q2"]
        lines.append(f"Pair #{idx} | Cosine Similarity: {p['similarity']:.4f}")
        lines.append(f"  [Q1] ID: {q1.get('id')} ({q1.get('difficulty')}, {q1.get('category')}): {q1.get('questionText')}")
        lines.append(f"  [Q2] ID: {q2.get('id')} ({q2.get('difficulty')}, {q2.get('category')}): {q2.get('questionText')}")
        lines.append("")

    lines.append("================================================================================")
    lines.append(f"Total Catalogue Near-Duplicate Pairs Identified: {len(java_pairs) + len(dbms_pairs)}")
    lines.append("Note: Catalogue content was NOT edited or deleted (preserved per specification).")
    lines.append("Selection logic MUST avoid serving both questions of any pair in the same session.")
    lines.append("================================================================================\n")

    content = "\n".join(lines)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(content)
    print(f"Report saved to {out_file}")


if __name__ == "__main__":
    main()
