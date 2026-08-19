"""
vector_store.py
----------------
Lightweight FAISS vector store wrapper used for the RAG layer that powers
SOP retrieval, drift-context lookup and AI SOP generation.

If the `faiss` package is not installed in the runtime environment, the
store transparently falls back to a brute-force cosine-similarity search
over a NumPy matrix -- functionally identical for the dataset sizes used
in this MVP (a few hundred SOP chunks), so the app never breaks.
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Dict

try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except Exception:
    _HAS_FAISS = False


class VectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.texts: List[str] = []
        self.metadata: List[Dict] = []
        self._matrix = None

        if _HAS_FAISS:
            self.index = faiss.IndexFlatL2(dim)
        else:
            self.index = None

    @property
    def backend(self) -> str:
        return "FAISS (IndexFlatL2)" if _HAS_FAISS else "NumPy brute-force cosine (FAISS fallback)"

    def add(self, vectors: np.ndarray, texts: List[str], metadata: List[Dict] = None):
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if metadata is None:
            metadata = [{} for _ in texts]

        if _HAS_FAISS:
            self.index.add(vectors)
        else:
            self._matrix = vectors if self._matrix is None else np.vstack([self._matrix, vectors])

        self.texts.extend(texts)
        self.metadata.extend(metadata)

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        query_vec = np.asarray(query_vec, dtype="float32").reshape(1, -1)
        n = len(self.texts)
        if n == 0:
            return []
        top_k = min(top_k, n)

        if _HAS_FAISS:
            distances, indices = self.index.search(query_vec, top_k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                score = 1.0 / (1.0 + float(dist))  # convert L2 distance to a 0-1-ish similarity
                results.append((self.texts[idx], score, self.metadata[idx]))
            return results

        # numpy fallback: cosine similarity
        mat = self._matrix
        q = query_vec[0]
        denom = (np.linalg.norm(mat, axis=1) * np.linalg.norm(q) + 1e-8)
        sims = (mat @ q) / denom
        top_idx = np.argsort(-sims)[:top_k]
        return [(self.texts[i], float(sims[i]), self.metadata[i]) for i in top_idx]

    def __len__(self):
        return len(self.texts)
