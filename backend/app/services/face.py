"""Face embedding provider with InsightFace and a deterministic mock fallback."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache

import numpy as np
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EMBEDDING_DIM = 512


class FaceService:
    def __init__(self) -> None:
        self._app = None
        self.provider = settings.face_provider
        if self.provider == "insightface":
            try:
                from insightface.app import FaceAnalysis

                self._app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
                self._app.prepare(ctx_id=-1, det_size=(640, 640))
                logger.info("InsightFace buffalo_l loaded")
            except Exception as exc:  # noqa: BLE001
                logger.warning("InsightFace unavailable (%s), using mock embeddings", exc)
                self.provider = "mock"
                self._app = None

    def embed_image_bytes(self, data: bytes) -> np.ndarray:
        from io import BytesIO

        img = Image.open(BytesIO(data)).convert("RGB")
        arr = np.asarray(img)
        return self.embed_array(arr)

    def embed_array(self, rgb: np.ndarray) -> np.ndarray:
        if self._app is not None:
            faces = self._app.get(rgb[:, :, ::-1])  # BGR for insightface
            if not faces:
                raise ValueError("Yuz topilmadi")
            faces = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
            emb = faces[0].normed_embedding.astype(np.float32)
            if emb.shape[0] != EMBEDDING_DIM:
                # pad or truncate
                out = np.zeros(EMBEDDING_DIM, dtype=np.float32)
                n = min(EMBEDDING_DIM, emb.shape[0])
                out[:n] = emb[:n]
                return out
            return emb
        return self._mock_embedding(rgb)

    def _mock_embedding(self, rgb: np.ndarray) -> np.ndarray:
        """Deterministic pseudo-embedding (dev). Same photo → same vector."""
        small = np.asarray(Image.fromarray(rgb).resize((48, 48), Image.Resampling.BILINEAR))
        h = hashlib.sha256(small.tobytes()).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], "little"))
        vec = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        vec /= np.linalg.norm(vec) + 1e-9
        return vec


@lru_cache
def get_face_service() -> FaceService:
    return FaceService()


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(1.0 - np.dot(a, b))
