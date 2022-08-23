import asyncio
from itertools import count
from os import getenv
from pathlib import Path

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
        finally:
            bridge_director.update_credentials()
        await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    asyncio.run(main())
