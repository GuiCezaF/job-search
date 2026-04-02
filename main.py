import asyncio
import sys
import argparse
from src.utils.config_loader import ConfigLoader
from src.utils.logger import AppLogger
from src.scraper.linkedin_scraper import LinkedInScraper
from src.storage.file_manager import FileManager
from src.notifier.discord_client import DiscordNotifier
from src.scheduler import JobScheduler

logger = AppLogger.setup_logger("Main")

async def run_job_search():
    logger.info("Iniciando ciclo de busca de vagas...")
    try:
        config = ConfigLoader()
        scraper = LinkedInScraper(config.linkedin_username, config.linkedin_password)
        
        # Executa a busca
        results = await scraper.run_scrape(
            config.search_keywords, 
            config.locations, 
            config.experience_levels
        )
        
        # Salva resultados
        file_manager = FileManager()
        file_path = file_manager.save_to_csv(results)
        
        # Notifica no Discord
        notifier = DiscordNotifier(config.discord_webhook)
        notifier.send_notification(results, file_path)
        
        logger.info("Ciclo de busca finalizado com sucesso.")
    except Exception as e:
        logger.error(f"Erro durante a execução do job: {e}")

def main():
    parser = argparse.ArgumentParser(description="Job Search Automation Service")
    parser.add_argument("--now", action="store_true", help="Executa a busca imediatamente e encerra.")
    args = parser.parse_args()

    # Função wrapper para rodar o job async no scheduler
    def sync_job_wrapper():
        asyncio.run(run_job_search())

    if args.now:
        sync_job_wrapper()
        sys.exit(0)
    
    # Se não for --now, inicia o agendador contínuo
    try:
        config = ConfigLoader()
        scheduler = JobScheduler(config.schedule, sync_job_wrapper)
        scheduler.start()
    except Exception as e:
        logger.error(f"Falha ao iniciar o serviço: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
