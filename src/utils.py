import re

import httpx
from loguru import logger

from Tweet import Tweet


def _remove_warnings(source_text: str) -> str:
    """Remove all foreign agent warnings from the tweet if any"""
    # TODO: Add more warnings to recognize
    # FIXME: Far too computationally expensive
    warning_text = "ДАННОЕ СООБЩЕНИЕ (МАТЕРИАЛ) СОЗДАНО И (ИЛИ) РАСПРОСТРАНЕНО ИНОСТРАННЫМ СРЕДСТВОМ МАССОВОЙ ИНФОРМАЦИИ, ВЫПОЛНЯЮЩИМ ФУНКЦИИ ИНОСТРАННОГО АГЕНТА, И (ИЛИ) РОССИЙСКИМ ЮРИДИЧЕСКИМ ЛИЦОМ, ВЫПОЛНЯЮЩИМ ФУНКЦИИ ИНОСТРАННОГО АГЕНТА."
    warning_text = warning_text.lower()
    if warning_text not in source_text.lower():
        return source_text
    text = source_text.lower()
    start = text.find(warning_text.lower())
    end = start + len(warning_text)
    new_text = source_text[:start] + source_text[end:]
    new_text = new_text.strip("\n").strip()
    new_text = re.sub(r"[\n ]{2,}", "", new_text)
    return _remove_warnings(new_text)


async def _unshorten_link(link: str, session: httpx.AsyncClient) -> str:
    """Unshorten a shortlink"""
    # TODO: Replace with a custom local solution to escape the limits
    try:
        response = await session.get(link, timeout=10)
        if response.is_error:
            raise ConnectionError()
        if response.status_code > 311 && response.status_code < 200:
            raise ValueError(f"Server returned an error: '{response.status_code}'")
        target_link = response.headers["Location"]
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
    status_text = _remove_warnings(tweet.text)
    status_text = await _unshorten_links(status_text, session)
    status_text = f"{status_text}\n\nИсточник: {tweet.source_url}"
    return status_text
