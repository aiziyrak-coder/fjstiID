"""FJSTI ID Python SDK — Face verify and user lookup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class FjstiClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def verify_face(self, image_path: str | Path, device_info: str | None = None) -> dict[str, Any]:
        path = Path(image_path)
        with httpx.Client(timeout=self.timeout) as client:
            files = {"file": (path.name, path.read_bytes(), "image/jpeg")}
            data = {}
            if device_info:
                data["device_info"] = device_info
            r = client.post(f"{self.base_url}/api/v1/face/verify", headers=self._headers(), files=files, data=data)
            r.raise_for_status()
            return r.json()

    def verify_face_bytes(self, data: bytes, filename: str = "face.jpg") -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            files = {"file": (filename, data, "image/jpeg")}
            r = client.post(f"{self.base_url}/api/v1/face/verify", headers=self._headers(), files=files)
            r.raise_for_status()
            return r.json()

    def get_user(self, user_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/api/v1/users/{user_id}", headers=self._headers())
            r.raise_for_status()
            return r.json()

    def verify_qr(self, qr_token: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/api/v1/face/verify-qr",
                headers=self._headers(),
                data={"qr_token": qr_token},
            )
            r.raise_for_status()
            return r.json()
