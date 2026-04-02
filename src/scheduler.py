from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class JobScheduler:
    """
    Agenda execução periódica do job via APScheduler (cron).

    O callback permanece síncrono para compatibilidade com BlockingScheduler;
    dentro dele o asyncio.run executa a corrida assíncrona.
    """

    def __init__(self, cron_expression: str, job_function: Callable[[], None]) -> None:
        if not cron_expression or not cron_expression.strip():
            raise ValueError("cron_expression não pode ser vazio")

        self.scheduler = BlockingScheduler()
        self.cron_expression = cron_expression.strip()
        self.job_function = job_function

    def start(self) -> None:
        logger.info(
            "Iniciando agendador",
            extra={"extra_fields": {"cron": self.cron_expression}},
        )
        try:
            self.scheduler.add_job(
                self.job_function,
                CronTrigger.from_crontab(self.cron_expression),
                id="job_search_task",
            )
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Agendador interrompido.")
            self.scheduler.shutdown()
        except Exception as err:
            logger.error(
                "Erro fatal no agendador",
                extra={"extra_fields": {"function": "start", "error": str(err)}},
                exc_info=True,
            )
            raise

    def run_now(self) -> None:
        logger.info("Executando job manualmente agora...")
        self.job_function()
