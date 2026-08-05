import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClientApp, WebhookDelivery

logger = logging.getLogger(__name__)


async def dispatch_webhooks(db: AsyncSession, event: str, payload: dict[str, Any]) -> None:
    result = await db.execute(
        __import__("sqlalchemy").select(ClientApp).where(
            ClientApp.is_active.is_(True), ClientApp.webhook_url.is_not(None)
        )
    )
    apps = result.scalars().all()
    async with httpx.AsyncClient(timeout=5.0) as client:
        for app in apps:
            if not app.webhook_url:
                continue
            success = False
            code = None
            try:
                resp = await client.post(
                    app.webhook_url,
                    json={"event": event, "data": payload},
                    headers={"X-FJSTI-Event": event},
                )
                code = resp.status_code
                success = 200 <= resp.status_code < 300
            except Exception as exc:  # noqa: BLE001
                logger.warning("Webhook to %s failed: %s", app.webhook_url, exc)
            db.add(
                WebhookDelivery(
                    client_app_id=app.id,
                    event=event,
                    payload=payload,
                    success=success,
                    response_code=code,
                )
            )
