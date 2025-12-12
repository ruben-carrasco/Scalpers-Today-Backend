from enum import Enum


class Currency(str, Enum):
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
