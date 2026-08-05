"""
Locust load test for FaceID verify endpoint.
Usage:
  locust -f scripts/locust_face.py --host http://localhost:8000
"""

import os
from io import BytesIO

from locust import HttpUser, between, task
from PIL import Image


def _dummy_jpeg() -> bytes:
    img = Image.new("RGB", (320, 320), color=(40, 80, 60))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


JPEG = _dummy_jpeg()
API_KEY = os.getenv("FJSTI_API_KEY", "")


class FaceVerifyUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def verify(self):
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        self.client.post(
            "/api/v1/face/verify",
            files={"file": ("t.jpg", JPEG, "image/jpeg")},
            headers=headers,
            name="/api/v1/face/verify",
        )

    @task(2)
    def health(self):
        self.client.get("/health")
