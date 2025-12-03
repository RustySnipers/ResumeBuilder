"""Webhook Background Worker

Continuously processes pending webhook events and handles retries.

This worker:
- Processes pending webhook events (newly created)
- Processes retry events (failed events ready for retry)
- Handles graceful shutdown on SIGTERM/SIGINT
- Provides health monitoring
- Logs processing statistics

Usage:
    python -m backend.webhooks.worker
"""

import asyncio
import signal
import logging
from datetime import datetime
from typing import Optional
import sys
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.webhooks.service import WebhookService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


class WebhookWorker:
    """Background worker for processing webhook events."""

    def __init__(
        self,
        database_url: str,
        pending_batch_size: int = 100,
        retry_batch_size: int = 100,
        sleep_seconds: int = 10,
    ):
        """Initialize webhook worker.

        Args:
            database_url: Database connection URL
            pending_batch_size: Number of pending events to process per cycle
            retry_batch_size: Number of retry events to process per cycle
            sleep_seconds: Seconds to sleep between processing cycles
        """
        self.database_url = database_url
        self.pending_batch_size = pending_batch_size
        self.retry_batch_size = retry_batch_size
        self.sleep_seconds = sleep_seconds

        self.running = False
        self.shutdown_event = asyncio.Event()

        # Statistics
        self.start_time: Optional[datetime] = None
        self.total_pending_processed = 0
        self.total_retry_processed = 0
        self.total_cycles = 0
        self.last_cycle_time: Optional[datetime] = None

        # Database engine
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize database connection."""
        logger.info("Initializing webhook worker...")

        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

        # Create session factory
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"Database connection initialized: {self.database_url}")

    async def shutdown(self):
        """Shutdown worker and close connections."""
        logger.info("Shutting down webhook worker...")

        self.running = False
        self.shutdown_event.set()

        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

        # Log final statistics
        self.log_statistics()

        logger.info("Webhook worker shutdown complete")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

    async def process_pending_events(self, session: AsyncSession) -> int:
        """Process pending webhook events.

        Args:
            session: Database session

        Returns:
            Number of events processed
        """
        try:
            webhook_service = WebhookService(session)
            processed = await webhook_service.process_pending_events(
                limit=self.pending_batch_size
            )

            if processed > 0:
                logger.info(f"Processed {processed} pending webhook events")

            return processed

        except Exception as e:
            logger.error(f"Error processing pending events: {e}", exc_info=True)
            return 0

    async def process_retry_events(self, session: AsyncSession) -> int:
        """Process retry webhook events.

        Args:
            session: Database session

        Returns:
            Number of events processed
        """
        try:
            webhook_service = WebhookService(session)
            processed = await webhook_service.process_retry_events(
                limit=self.retry_batch_size
            )

            if processed > 0:
                logger.info(f"Processed {processed} retry webhook events")

            return processed

        except Exception as e:
            logger.error(f"Error processing retry events: {e}", exc_info=True)
            return 0

    async def process_cycle(self):
        """Process one cycle of webhook events."""
        cycle_start = datetime.utcnow()

        try:
            async with self.async_session() as session:
                # Process pending events
                pending_processed = await self.process_pending_events(session)
                self.total_pending_processed += pending_processed

                # Process retry events
                retry_processed = await self.process_retry_events(session)
                self.total_retry_processed += retry_processed

                # Update statistics
                self.total_cycles += 1
                self.last_cycle_time = datetime.utcnow()

                # Log cycle summary if any events were processed
                if pending_processed > 0 or retry_processed > 0:
                    cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                    logger.info(
                        f"Cycle {self.total_cycles} complete: "
                        f"{pending_processed} pending, {retry_processed} retry "
                        f"({cycle_duration:.2f}s)"
                    )

        except Exception as e:
            logger.error(f"Error in processing cycle: {e}", exc_info=True)

    def log_statistics(self):
        """Log worker statistics."""
        if not self.start_time:
            return

        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        uptime_hours = uptime / 3600

        logger.info("=" * 60)
        logger.info("Webhook Worker Statistics")
        logger.info("=" * 60)
        logger.info(f"Uptime: {uptime_hours:.2f} hours")
        logger.info(f"Total cycles: {self.total_cycles}")
        logger.info(f"Pending events processed: {self.total_pending_processed}")
        logger.info(f"Retry events processed: {self.total_retry_processed}")
        logger.info(f"Total events processed: {self.total_pending_processed + self.total_retry_processed}")

        if self.total_cycles > 0:
            avg_per_cycle = (self.total_pending_processed + self.total_retry_processed) / self.total_cycles
            logger.info(f"Average events per cycle: {avg_per_cycle:.2f}")

        if self.last_cycle_time:
            logger.info(f"Last cycle: {self.last_cycle_time.isoformat()}")

        logger.info("=" * 60)

    async def run(self):
        """Run the webhook worker."""
        try:
            # Initialize
            await self.initialize()

            # Setup signal handlers
            self.setup_signal_handlers()

            # Start processing
            self.running = True
            self.start_time = datetime.utcnow()

            logger.info("Webhook worker started")
            logger.info(f"Pending batch size: {self.pending_batch_size}")
            logger.info(f"Retry batch size: {self.retry_batch_size}")
            logger.info(f"Sleep interval: {self.sleep_seconds}s")
            logger.info("Press Ctrl+C to stop")

            # Log statistics every hour
            last_stats_time = datetime.utcnow()
            stats_interval = 3600  # 1 hour

            # Main processing loop
            while self.running and not self.shutdown_event.is_set():
                # Process one cycle
                await self.process_cycle()

                # Log statistics periodically
                if (datetime.utcnow() - last_stats_time).total_seconds() >= stats_interval:
                    self.log_statistics()
                    last_stats_time = datetime.utcnow()

                # Sleep before next cycle
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.sleep_seconds
                    )
                    # If we get here, shutdown was signaled
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue to next cycle
                    pass

        except Exception as e:
            logger.error(f"Fatal error in webhook worker: {e}", exc_info=True)
            raise

        finally:
            await self.shutdown()

    def get_health_status(self) -> dict:
        """Get worker health status.

        Returns:
            Health status dictionary
        """
        if not self.running:
            return {
                "status": "stopped",
                "healthy": False,
            }

        # Check if last cycle was recent (within 2x sleep interval)
        if self.last_cycle_time:
            seconds_since_last_cycle = (datetime.utcnow() - self.last_cycle_time).total_seconds()
            healthy = seconds_since_last_cycle < (self.sleep_seconds * 2)
        else:
            healthy = True  # Just started

        uptime = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0

        return {
            "status": "running",
            "healthy": healthy,
            "uptime_seconds": uptime,
            "total_cycles": self.total_cycles,
            "total_events_processed": self.total_pending_processed + self.total_retry_processed,
            "pending_processed": self.total_pending_processed,
            "retry_processed": self.total_retry_processed,
            "last_cycle": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
        }


async def main():
    """Main entry point for webhook worker."""
    # Get configuration from environment
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Get optional configuration
    pending_batch_size = int(os.getenv("WEBHOOK_PENDING_BATCH_SIZE", "100"))
    retry_batch_size = int(os.getenv("WEBHOOK_RETRY_BATCH_SIZE", "100"))
    sleep_seconds = int(os.getenv("WEBHOOK_SLEEP_SECONDS", "10"))

    # Create and run worker
    worker = WebhookWorker(
        database_url=database_url,
        pending_batch_size=pending_batch_size,
        retry_batch_size=retry_batch_size,
        sleep_seconds=sleep_seconds,
    )

    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Webhook worker stopped by user")
    except Exception as e:
        logger.error(f"Webhook worker failed: {e}", exc_info=True)
        sys.exit(1)
