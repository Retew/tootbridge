import asyncio
import json
from pathlib import Path
from time import time

import httpx
from loguru import logger

from .Bridge import Bridge


class BridgeDirector:
    def __init__(self, credentials_path: Path, twitter_api: str) -> None:
        assert (
            credentials_path.exists()
        ), f"Invalid credentials path: '{credentials_path}'"
        self._twitter_api: str = twitter_api
        self._credentials_path: Path = credentials_path
        self._bridges: list[Bridge] = self._get_bridges()

    def _get_bridges(self) -> list[Bridge]:
        """Load up bridges from the json file"""
        with open(self._credentials_path, "r") as f:
            credentials: list[dict[str, str]] = json.load(f)
        assert credentials, "No credentials provided"
        bridges: list[Bridge] = [
            Bridge(
                mastodon_instance_url=bridge["HOST_INSTANCE"],
                mastodon_api_token=bridge["APP_SECURE_TOKEN"],
                twitter_acc_username=bridge["TWITTER_USERNAME"],
                last_relayed_tweet_id=int(bridge["LAST_POSTED_ID"]),
                twitter_api_url=self._twitter_api,
            )
            for bridge in credentials
        ]
        logger.info(f"Loaded up {len(bridges)} bridges")
        return bridges

    async def sync_bridges(self) -> None:
        """Get the latest tweets for every bridge and relay it to Mastodon"""
        start_time = time()
        logger.info("Synchronizing accounts")
        async with httpx.AsyncClient() as client:
            tasks = (bridge.synchronize_accounts(client) for bridge in self._bridges)
            await asyncio.gather(*tasks)
        timedelta = time() - start_time
        logger.info(f"Run finished. Run duration: {round(timedelta, 3)}s")

    def update_credentials(self) -> None:
        """Dump updated data into the json file"""
        updated_credentials = [
            {
                "TWITTER_USERNAME": bridge.twitter_acc_username,
                "HOST_INSTANCE": bridge.mastodon_instance_url,
                "LAST_POSTED_ID": bridge.last_relayed_tweet_id,
                "APP_SECURE_TOKEN": bridge.mastodon_api_token,
            }
            for bridge in self._bridges
        ]

        with open(self._credentials_path, "w") as f:
            json.dump(updated_credentials, f, indent=4)

        logger.info("Updated credentials data")
