import asyncio
import signal
from functools import partial
from itertools import count
from os import getenv
from pathlib import Path
from typing import Any

from loguru import logger

from tootbridge import BridgeDirector


@logger.catch()
async def main() -> None:
    credentials_path = Path("credentials.json")
    twitter_api: str = getenv("TWITTER_API_URL", "")
    assert twitter_api, "Twitter API url is missing"
    bridge_director = BridgeDirector(credentials_path, twitter_api)
    sleep_duration: float = float(getenv("SLEEP_DURATION", 60))
    logger.info(f"Polling frequency is set to {sleep_duration}s")
    logger.info("Tootbridge daemon started")

    for i in count(start=1):
        logger.debug(f"Run {i} started")
        try:
            await bridge_director.sync_bridges()
            bridge_director.update_credentials()
            await asyncio.sleep(sleep_duration)
        except asyncio.CancelledError:
            logger.warning("Shutting down now")
            bridge_director.update_credentials()
            break


def cancel_coroutine(target_coroutine: Any):
    """A signal handler that cancels running tasks for the target coroutine"""
    for task in asyncio.tasks.all_tasks():
        if task.get_coro() is target_coroutine and not task.cancelled():
            task.cancel()


if __name__ == "__main__":
    main_task = main()
    cancel_main_task = partial(cancel_coroutine, target_coroutine=main_task)
    loop = asyncio.new_event_loop()
    loop.add_signal_handler(signal.SIGINT, cancel_main_task)
    loop.add_signal_handler(signal.SIGTERM, cancel_main_task)
    loop.run_until_complete(main_task)
