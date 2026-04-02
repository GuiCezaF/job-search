import requests
import json
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_notification(self, data: list, file_path: str = None) -> None:
        if not data:
            self._send_raw_message("🚀 Busca finalizada: Nenhuma nova vaga encontrada hoje.")
            return

        summary = f"🚀 **Busca de Vagas Finalizada!**\n\nTotal encontradas: **{len(data)}**\n"
        
        # Pega as 5 primeiras para o resumo rápido
        summary += "--- 📋 Resumo (Top 5) ---\n"
        for job in data[:5]:
            summary += f"🔹 **{job['Título']}** @ {job['Empresa']} ({job['Local']})\n"
        
        if len(data) > 5:
            summary += f"\n...e mais {len(data) - 5} vagas encontradas."
            
        summary += f"\n\n📂 Arquivo do dia: `{file_path}`" if file_path else ""
        
        self._send_raw_message(summary)

    def _send_raw_message(self, content: str):
        payload = {"content": content}
        try:
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload), 
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.info("Notificação enviada para o Discord.")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação para Discord: {e}")
