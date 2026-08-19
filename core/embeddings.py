"""
embeddings.py
-------------
Embedding provider abstraction for Process Genome AI.

Resolution order (graceful degradation so the demo ALWAYS runs, with or
without live cloud credentials -- important for a hackathon jury laptop
with no internet):

    1. Azure OpenAI embeddings   (if AZURE_OPENAI_* env vars are set)
    2. sentence-transformers     (if the package + model are available locally)
    3. TF-IDF (scikit-learn)     (always available, zero external dependency)

The rest of the app (vector_store.py, rag_engine.py) only depends on the
`EmbeddingEngine.encode(texts) -> np.ndarray` contract, so swapping the
underlying provider never touches downstream code.
"""

from __future__ import annotations

import os
import numpy as np
from typing import List


class EmbeddingEngine:
    def __init__(self):
        self.backend = None
        self.model = None
        self._tfidf = None
        self._dim = 384

        # --- 1. Try Azure OpenAI -------------------------------------------------
        if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
            try:
                from openai import AzureOpenAI  # noqa: F401
                self.client = AzureOpenAI(
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                )
                self.deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
                self.backend = "azure_openai"
            except Exception:
                self.backend = None

        # --- 2. Try sentence-transformers ----------------------------------------
        if self.backend is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.backend = "sentence_transformers"
                self._dim = self.model.get_sentence_embedding_dimension()
            except Exception:
                self.backend = None

        # --- 3. Fallback: TF-IDF --------------------------------------------------
        if self.backend is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._TfidfVectorizer = TfidfVectorizer
            self.backend = "tfidf"

    @property
    def dimension(self) -> int:
        return self._dim

    def fit(self, corpus: List[str]):
        """Only relevant for the TF-IDF fallback -- needs a corpus to fit on."""
        if self.backend == "tfidf":
            self._tfidf = self._TfidfVectorizer(max_features=512, stop_words="english")
            matrix = self._tfidf.fit_transform(corpus).toarray().astype("float32")
            self._dim = matrix.shape[1]
            return matrix
        return None

    def encode(self, texts: List[str]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        if self.backend == "azure_openai":
            resp = self.client.embeddings.create(model=self.deployment, input=texts)
            vecs = np.array([d.embedding for d in resp.data], dtype="float32")
            self._dim = vecs.shape[1]
            return vecs

        if self.backend == "sentence_transformers":
            return np.asarray(self.model.encode(texts), dtype="float32")

        # tfidf fallback -- must already be fitted via .fit()
        if self._tfidf is None:
            self.fit(texts)
        vecs = self._tfidf.transform(texts).toarray().astype("float32")
        # pad / truncate to fixed dim for consistency with FAISS index
        if vecs.shape[1] < self._dim:
            pad = np.zeros((vecs.shape[0], self._dim - vecs.shape[1]), dtype="float32")
            vecs = np.hstack([vecs, pad])
        elif vecs.shape[1] > self._dim:
            vecs = vecs[:, : self._dim]
        return vecs

    def label(self) -> str:
        return {
            "azure_openai": "Azure OpenAI Embeddings (text-embedding-3-small)",
            "sentence_transformers": "sentence-transformers (all-MiniLM-L6-v2, local)",
            "tfidf": "TF-IDF vectorizer (offline fallback)",
        }[self.backend]
