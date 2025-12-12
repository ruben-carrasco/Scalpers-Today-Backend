from enum import Enum


class Timezone(str, Enum):
    UTC = "UTC"
    EUROPE_MADRID = "Europe/Madrid"
    AMERICA_NEW_YORK = "America/New_York"
    ASIA_TOKYO = "Asia/Tokyo"
