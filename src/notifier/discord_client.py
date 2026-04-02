from typing import Any, List, Mapping, Optional

import httpx

from src.types.exceptions import ReportingError
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class DiscordNotifier:
    """Post job-search summaries to Discord via incoming webhook (async HTTP)."""

    def __init__(self, webhook_url: str) -> None:
        """``webhook_url``: Discord incoming webhook URL."""
        if not webhook_url or not webhook_url.strip():
            raise ValueError("webhook_url must not be empty")

        self.webhook_url = webhook_url.strip()

    async def send_notification(
        self,
        data: List[Mapping[str, Any]],
        file_path: Optional[str] = None,
    ) -> None:
        """Send a formatted message; ``data`` rows use Portuguese CSV column keys."""
        if not data:
            await self._send_raw_message(
                "Job search finished: no jobs found today."
            )
            return

        summary = (
            f"**Job search finished**\n\nTotal: **{len(data)}**\n"
        )
        summary += "--- Top 5 ---\n"
        for job in data[:5]:
            summary += f"**{job['Título']}** @ {job['Empresa']} ({job['Local']})\n"
            summary += f"[Open job]({job['Link']})\n\n"

        if len(data) > 5:
            summary += f"...and {len(data) - 5} more."

        if file_path:
            summary += f"\n\nCSV: `{file_path}`"

        await self._send_raw_message(summary)

    async def _send_raw_message(self, content: str) -> None:
        """POST JSON body to the webhook; raises ``ReportingError`` on HTTP failure."""
        payload = {"content": content}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            logger.info("Discord notification sent.")
        except httpx.HTTPError as err:
            logger.error(
                "HTTP error sending Discord notification",
                extra={"extra_fields": {"function": "_send_raw_message", "error": str(err)}},
            )
            raise ReportingError("Failed to send Discord webhook") from err
