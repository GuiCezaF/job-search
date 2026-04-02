from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self, cron_expression: str, job_function):
        self.scheduler = BlockingScheduler()
        self.cron_expression = cron_expression
        self.job_function = job_function

    def start(self):
        logger.info(f"Iniciando agendador com cron: {self.cron_expression}")
        try:
            self.scheduler.add_job(
                self.job_function,
                CronTrigger.from_crontab(self.cron_expression),
                id='job_search_task'
            )
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Agendador interrompido.")
            self.scheduler.shutdown()
        except Exception as e:
            logger.error(f"Erro fatal no agendador: {e}")
            raise

    def run_now(self):
        logger.info("Executando job manualmente agora...")
        self.job_function()
