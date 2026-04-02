from typing import Any, List, Mapping, Optional

import httpx

from src.types.exceptions import ReportingError
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class DiscordNotifier:
    """
    Envia resumo de vagas ao Discord via webhook (HTTP assíncrono).
    """

    def __init__(self, webhook_url: str) -> None:
        if not webhook_url or not webhook_url.strip():
            raise ValueError("webhook_url não pode ser vazio")

        self.webhook_url = webhook_url.strip()

    async def send_notification(
        self,
        data: List[Mapping[str, Any]],
        file_path: Optional[str] = None,
    ) -> None:
        if not data:
            await self._send_raw_message(
                "🚀 Busca finalizada: Nenhuma nova vaga encontrada hoje."
            )
            return

        summary = (
            f"🚀 **Busca de Vagas Finalizada!**\n\nTotal encontradas: **{len(data)}**\n"
        )
        summary += "--- 📋 Resumo (Top 5) ---\n"
        for job in data[:5]:
            summary += f"🔹 **{job['Título']}** @ {job['Empresa']} ({job['Local']})\n"
            summary += f"🔗 [Ver Vaga]({job['Link']})\n\n"

        if len(data) > 5:
            summary += f"💡 ...e mais {len(data) - 5} vagas encontradas."

        if file_path:
            summary += f"\n\n📂 Arquivo do dia: `{file_path}`"

        await self._send_raw_message(summary)

    async def _send_raw_message(self, content: str) -> None:
        payload = {"content": content}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            logger.info("Notificação enviada para o Discord.")
        except httpx.HTTPError as err:
            logger.error(
                "Erro HTTP ao enviar notificação para Discord",
                extra={"extra_fields": {"function": "_send_raw_message", "error": str(err)}},
            )
            raise ReportingError("Falha ao enviar webhook do Discord") from err
