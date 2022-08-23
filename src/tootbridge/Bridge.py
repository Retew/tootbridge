import contextlib
from asyncio import Queue
from dataclasses import dataclass, field

import httpx
from loguru import logger

from .Tweet import Tweet
from .utils import prepare_text


@dataclass
class Bridge:
    """A single bridge account including associated Twitter and Mastodon account"""

    mastodon_instance_url: str
    mastodon_api_token: str
    twitter_acc_username: str
    last_relayed_tweet_id: int
    twitter_api_url: str
    _pending_tweets: Queue[Tweet] = field(default_factory=Queue)

    async def synchronize_accounts(self, client_: httpx.AsyncClient) -> None:
        """Retrieve all the latest tweets and relay them to Mastodon"""
        await self._gather_new_tweets(client_)
        await self._relay_new_tweets(client_)

    async def _gather_new_tweets(self, client_: httpx.AsyncClient) -> None:
        """Retrieve latest tweets"""
        response = await client_.get(
            f"{self.twitter_api_url}/{self.twitter_acc_username}"
        )

        if response.is_error:
            logger.error(
                f"Error retrieving new tweets for @{self.twitter_acc_username}. Server returned code {response.status_code} - {response.text}"
            )
            return

        response_payload: list[dict[str, str]] = response.json()
        new_tweets_cnt: int = 0

        for tweet_data in response_payload[::-1]:
            tweet = Tweet(
                text=tweet_data["full_text"],
                source_url=tweet_data["ext_urlstatus"],
                tweet_id=int(tweet_data["id_str"]),
            )

            # ignore the tweet if it has already been posted
            if tweet.tweet_id <= self.last_relayed_tweet_id:
                continue

            await self._pending_tweets.put(tweet)
            new_tweets_cnt += 1

        logger.info(
            f"Gathered {new_tweets_cnt} new tweets for account @{self.twitter_acc_username}"
        )

    async def _relay_new_tweets(self, client_: httpx.AsyncClient) -> None:
        """Post a new status with a link pointing to it's source on Twitter"""
        while not self._pending_tweets.empty():
            tweet: Tweet = await self._pending_tweets.get()
            status_text = await prepare_text(tweet, client_)

            with contextlib.suppress(httpx.RequestError):
                status_id = await self._post_status(status_text, client_)
                logger.info(
                    f"Tweet {tweet.tweet_id} from @{self.twitter_acc_username} posted to Mastodon under id {status_id}"
                )
                self.last_relayed_tweet_id = tweet.tweet_id

    async def _post_status(self, text: str, client_: httpx.AsyncClient) -> str:
        """Post a new status and return its ID"""
        url: str = f"{self.mastodon_instance_url}/api/v1/statuses"
        response: httpx.Response = await client_.post(
            url=url,
            headers={"Authorization": f"Bearer {self.mastodon_api_token}"},
            data={"status": text, "visibility": "unlisted"},
        )

        if response.is_error:
            message = f"Error posting status for @{self.twitter_acc_username}. Server returned code {response.status_code} - {response.text}"
            logger.error(message)
            raise httpx.RequestError(message)

        return str(response.json()["id"])
