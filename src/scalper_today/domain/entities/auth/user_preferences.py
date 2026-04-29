from dataclasses import dataclass

from .currency import Currency
from .language import Language
from .timezone_enum import Timezone


@dataclass
class UserPreferences:
    language: Language = Language.ES
    currency: Currency = Currency.USD
    timezone: Timezone = Timezone.EUROPE_MADRID
