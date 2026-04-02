import argparse
import asyncio
import sys
from typing import NoReturn

from src.notifier.discord_client import DiscordNotifier
from src.scheduler import JobScheduler
from src.scraper.linkedin_scraper import LinkedInScraper
from src.storage.file_manager import FileManager
from src.storage.google_drive_uploader import GoogleDriveUploader
from src.types.exceptions import AppError, ConfigError, LoginError, ReportingError
from src.utils.config_loader import ConfigLoader
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger("Main")


def _exit_with_error(message: str, *, exc_info: bool = False) -> NoReturn:
    """Log an error and terminate the process with exit code 1."""
    logger.error(
        message,
        extra={"extra_fields": {"exit_code": 1}},
        exc_info=exc_info,
    )
    sys.exit(1)


async def run_job_search() -> None:
    """Run one full cycle: scrape, save CSV, optional Drive upload, notify Discord. Swallows expected errors after logging."""
    logger.info("Starting job search cycle...")
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

        gd = app_cfg.google_drive
        if file_path and gd.folder_id.strip() and not gd.enabled:
            logger.info(
                "Google Drive upload skipped: google_drive.enabled is false "
                "(folder_id is set; set enabled: true to upload the CSV).",
                extra={"extra_fields": {"function": "run_job_search"}},
            )

        if app_cfg.google_drive.enabled and file_path:
            try:
                uploader = GoogleDriveUploader(app_cfg.google_drive.folder_id)
                await asyncio.to_thread(uploader.upload_file, file_path)
            except ReportingError as err:
                logger.error(
                    "Google Drive upload failed; continuing with Discord notification",
                    extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
                )

        notifier = DiscordNotifier(app_cfg.discord.webhook_url.get_secret_value())
        await notifier.send_notification(results, file_path)

        logger.info("Job search cycle completed.")
    except ConfigError as err:
        logger.error(
            "Invalid or missing configuration",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except LoginError as err:
        logger.error(
            "LinkedIn authentication failed",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except ReportingError as err:
        logger.error(
            "Export or notification failed",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except AppError as err:
        logger.error(
            "Application error",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
        )
    except Exception as err:
        logger.error(
            "Unexpected error during job run",
            extra={"extra_fields": {"function": "run_job_search", "error": str(err)}},
            exc_info=True,
        )


def main() -> None:
    """CLI entry: either run once (--now) or start the cron scheduler."""
    parser = argparse.ArgumentParser(description="Job Search Automation Service")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run one search cycle and exit.",
    )
    args = parser.parse_args()

    def sync_job_wrapper() -> None:
        """Runs the async job pipeline inside a new event loop (for APScheduler)."""
        asyncio.run(run_job_search())

    if args.now:
        sync_job_wrapper()
        return

    try:
        loader = ConfigLoader()
        scheduler = JobScheduler(loader.app_config.search.schedule, sync_job_wrapper)
        scheduler.start()
    except ConfigError as err:
        _exit_with_error(f"Configuration error: {err}")
    except Exception as err:
        _exit_with_error(f"Failed to start service: {err}", exc_info=True)


if __name__ == "__main__":
    main()
