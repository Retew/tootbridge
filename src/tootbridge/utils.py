import re

import httpx
from loguru import logger

from .Tweet import Tweet


async def _unshorten_link(link: str, session: httpx.AsyncClient) -> str:
    """Unshorten a shortlink"""
    try:
        response = await session.head(link, timeout=10)
        if response.is_error:
            raise ConnectionError(f"Server returned an error: '{response.status_code}'")
        target_link: str = response.headers.get("Location", "")
        if not target_link:
            raise ValueError("Server returned an empty link")
        return target_link
    except Exception as e:
        logger.error(f"Failed to unshorten link '{link}'. {e}")
        return link


async def _unshorten_links(text: str, session: httpx.AsyncClient) -> str:
    """Find all the Twitter-shortened links in the text and unshorten them"""
    link_pattern = r"https://t.co/[a-zA-Z0-9]+"
    for link in re.findall(link_pattern, text):
        replacement = await _unshorten_link(link, session)
        text = text.replace(link, replacement)
    return text


async def prepare_text(tweet: Tweet, session: httpx.AsyncClient) -> str:
    """Prepare status text before posting"""
    status_text = tweet.text
    status_text = await _unshorten_links(status_text, session)
    status_text = f"{status_text}\n\nИсточник: {tweet.source_url}"
    return status_text
