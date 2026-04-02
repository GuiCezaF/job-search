import argparse
import asyncio
import sys
from typing import NoReturn

from src.notifier.discord_client import DiscordNotifier
from src.scheduler import JobScheduler
from src.scraper.linkedin_scraper import LinkedInScraper
from src.storage.file_manager import FileManager
from src.types.exceptions import AppError, ConfigError, LoginError, ReportingError
from src.utils.config_loader import ConfigLoader
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger("Main")


def _exit_with_error(message: str, *, exc_info: bool = False) -> NoReturn:
    logger.error(
        message,
        extra={"extra_fields": {"exit_code": 1}},
        exc_info=exc_info,
    )
    sys.exit(1)


async def run_job_search() -> None:
    """Orquestra scrape, persistência e notificação (fluxo assíncrono de I/O)."""
    logger.info("Iniciando ciclo de busca de vagas...")
    try:
        loader = ConfigLoader()
        app_cfg = loader.app_config

        scraper = LinkedInScraper(
            app_cfg.linkedin.username,
            app_cfg.linkedin.password.get_secret_value(),
            max_jobs_per_query=app_cfg.search.max_jobs_per_query,
        )
        results = await scraper.run_scrape(
            app_cfg.search.keywords,
            app_cfg.search.locations,
            app_cfg.search.experience_levels,
        )

        file_manager = FileManager()
        file_path = file_manager.save_to_csv(results)

        notifier = DiscordNotifier(app_cfg.discord.webhook_url.get_secret_value())
        await notifier.send_notification(results, file_path)

        logger.info("Ciclo de busca finalizado com sucesso.")
    except ConfigError as err:
        logger.error(
            "Configuração inválida ou ausente",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except LoginError as err:
        logger.error(
            "Falha de autenticação no LinkedIn",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except ReportingError as err:
        logger.error(
            "Falha ao notificar ou exportar resultados",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except AppError as err:
        logger.error(
            "Erro da aplicação",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except Exception as err:
        logger.error(
            "Erro inesperado durante a execução do job",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
            exc_info=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Search Automation Service")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Executa a busca imediatamente e encerra.",
    )
    args = parser.parse_args()

    def sync_job_wrapper() -> None:
        asyncio.run(run_job_search())

    if args.now:
        sync_job_wrapper()
        return

    try:
        loader = ConfigLoader()
        scheduler = JobScheduler(loader.app_config.search.schedule, sync_job_wrapper)
        scheduler.start()
    except ConfigError as err:
        _exit_with_error(f"Falha de configuração: {err}")
    except Exception as err:
        _exit_with_error(f"Falha ao iniciar o serviço: {err}", exc_info=True)


if __name__ == "__main__":
    main()
