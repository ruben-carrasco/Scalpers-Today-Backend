from enum import StrEnum


class AlertType(StrEnum):
    HIGH_IMPACT_EVENT = "high_impact_event"
    SPECIFIC_COUNTRY = "specific_country"
    SPECIFIC_CURRENCY = "specific_currency"
    DATA_RELEASE = "data_release"
    SURPRISE_MOVE = "surprise_move"
