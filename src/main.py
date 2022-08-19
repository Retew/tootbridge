import asyncio
import atexit
import json
from os import getenv
from time import time

import httpx
from loguru import logger

from Bridge import Bridge

BRIDGES: list[Bridge] = []


def get_bridges() -> list[Bridge]:
    with open("credentials.json", "r") as f:
        credentials: list[dict[str, str]] = json.load(f)
    assert credentials, "No credentials provided"
    twitter_api_url: str = getenv("TWITTER_API_URL", "")
    assert twitter_api_url, "Twitter API url is missing"
    bridges: list[Bridge] = [
        Bridge(
            mastodon_instance_url=bridge["HOST_INSTANCE"],
            mastodon_api_token=bridge["APP_SECURE_TOKEN"],
            twitter_acc_username=bridge["TWITTER_USERNAME"],
            last_relayed_tweet_id=int(bridge["LAST_POSTED_ID"]),
            twitter_api_url=twitter_api_url,
        )
        for bridge in credentials
    ]
    logger.info(f"Loaded up {len(bridges)} bridges")
    global BRIDGES
    BRIDGES = bridges
    return bridges


async def sync_bridges(bridges: list[Bridge]) -> None:
    start_time = time()
    logger.info("Synchronizing accounts")
    async with httpx.AsyncClient() as client:
        tasks = (bridge.synchronize_accounts(client) for bridge in bridges)
        await asyncio.gather(*tasks)
    timedelta = time() - start_time
    logger.info(f"Run finished. Run duration: {round(timedelta, 3)}s")


def update_credentials(bridges: list[Bridge]) -> None:
    updated_credentials = [
        {
            "TWITTER_USERNAME": bridge.twitter_acc_username,
            "HOST_INSTANCE": bridge.mastodon_instance_url,
            "LAST_POSTED_ID": bridge.last_relayed_tweet_id,
            "APP_SECURE_TOKEN": bridge.mastodon_api_token,
        }
        for bridge in bridges
    ]

    with open("credentials.json", "w") as f:
        json.dump(updated_credentials, f, indent=4)

    logger.info("Updated credentials data")


@atexit.register  # FIXME: Doesn't work in docker
def shutdown() -> None:
    logger.warning("Shutting down now")
    global BRIDGES
    update_credentials(BRIDGES)
    logger.info("Finished")


@logger.catch()
async def main() -> None:
    bridges: list[Bridge] = get_bridges()
    sleep_duration: float = float(getenv("SLEEP_DURATION", 60))
    logger.info(f"Polling frequency is set to {sleep_duration}s")

    while True:
        logger.debug("")
        await sync_bridges(bridges)
        update_credentials(bridges)
        await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    asyncio.run(main())
