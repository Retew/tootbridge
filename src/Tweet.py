from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tweet:
    """A single Tweet descriptor"""

    text: str
    source_url: str
    tweet_id: int
