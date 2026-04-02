from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class JobScheduler:
    """Run a synchronous callback on a cron schedule using APScheduler's blocking scheduler."""

    def __init__(self, cron_expression: str, job_function: Callable[[], None]) -> None:
        """``job_function`` must be sync; use ``asyncio.run`` inside it for async work."""
        if not cron_expression or not cron_expression.strip():
            raise ValueError("cron_expression must not be empty")

        self.scheduler = BlockingScheduler()
        self.cron_expression = cron_expression.strip()
        self.job_function = job_function

    def start(self) -> None:
        """Register the cron job and block until interrupt or error."""
        logger.info(
            "Starting scheduler",
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
            logger.info("Scheduler interrupted.")
            self.scheduler.shutdown()
        except Exception as err:
            logger.error(
                "Fatal scheduler error",
                extra={"extra_fields": {"function": "start", "error": str(err)}},
                exc_info=True,
            )
            raise

    def run_now(self) -> None:
        """Invoke the registered callback immediately."""
        logger.info("Running job manually.")
        self.job_function()
