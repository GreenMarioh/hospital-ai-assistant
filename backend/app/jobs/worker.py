"""Background worker: run with `python -m app.jobs.worker` (single instance)."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.jobs.reminders import send_due_reminders

log = logging.getLogger("app.jobs.worker")


async def reminder_tick() -> None:
    try:
        async with SessionLocal() as db:
            await send_due_reminders(db)
    except Exception:
        log.exception("reminder job failed")


async def main() -> None:
    setup_logging()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(reminder_tick, "interval", minutes=5, max_instances=1, coalesce=True)
    scheduler.start()
    log.info("worker started")
    await reminder_tick()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
