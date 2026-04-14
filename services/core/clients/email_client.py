"""Async email client — Resend with Jinja2 templates."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


class EmailClient:
    """Send emails via Resend API. Falls back to console logging if no API key."""

    def __init__(self, api_key: str, from_address: str):
        self._api_key = api_key
        self._from_address = from_address
        self._env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    async def send_magic_link(self, to_email: str, link: str) -> None:
        html = self._env.get_template("magic_link.html").render(link=link)
        subject = "Your login link — GenAlpha"
        await self._send(to_email, subject, html)

    async def _send(self, to: str, subject: str, html: str) -> None:
        if not self._api_key:
            logger.info("=== EMAIL (no Resend key, logging to console) ===")
            logger.info("To: %s", to)
            logger.info("Subject: %s", subject)
            logger.info("Body: %s", html[:200])
            logger.info("================================================")
            return

        try:
            import resend
            resend.api_key = self._api_key
            await asyncio.to_thread(
                resend.Emails.send,
                {
                    "from": self._from_address,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            logger.info("Email sent via Resend to %s", to)
        except Exception as e:
            logger.error("Resend email failed: %s — falling back to console", e)
            logger.info("To: %s | Subject: %s", to, subject)
