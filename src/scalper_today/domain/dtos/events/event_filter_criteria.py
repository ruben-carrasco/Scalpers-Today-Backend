from dataclasses import dataclass


@dataclass
class EventFilterCriteria:
    importance: int | None = None
    country: str | None = None
    has_data: bool | None = None
    search: str | None = None
