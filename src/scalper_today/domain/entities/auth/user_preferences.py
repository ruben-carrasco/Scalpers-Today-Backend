from dataclasses import dataclass

from .language import Language
from .currency import Currency
from .timezone_enum import Timezone


@dataclass
class UserPreferences:
    language: Language = Language.ES
    currency: Currency = Currency.USD
    timezone: Timezone = Timezone.EUROPE_MADRID
