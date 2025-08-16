import os
from dataclasses import dataclass
from typing import List, Optional
import pytz

@dataclass
class Settings:
    # Discord
    token: str
    channel_id: int
    guild_id: int = 0

    # Amadeus
    amadeus_host: str
    amadeus_client_id: Optional[str]
    amadeus_client_secret: Optional[str]

    # Búsqueda
    market: str
    origin: str
    tokyo_codes: List[str]
    osaka_codes: List[str]
    days_ahead: int
    stay_nights: int

    # Monedas
    primary_currency: str
    second_currency: str
    fx_usdclp: Optional[str]

    # Fechas fijas opcionales
    departure_date_env: str
    return_date_env: str

    # Zona horaria
    timezone_str: str = "America/Santiago"

    @property
    def tz(self):
        return pytz.timezone(self.timezone_str)

    @staticmethod
    def from_env() -> "Settings":
        def split_codes(v: str) -> List[str]:
            return [x.strip() for x in (v or "").split(",") if x.strip()]

        return Settings(
            token=os.getenv("DISCORD_TOKEN", ""),
            channel_id=int(os.getenv("DISCORD_CHANNEL_ID", "0")),
            guild_id=int(os.getenv("GUILD_ID", "0")),
            amadeus_host=os.getenv("AMADEUS_HOST", "https://test.api.amadeus.com"),
            amadeus_client_id=os.getenv("AMADEUS_CLIENT_ID"),
            amadeus_client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
            market=os.getenv("MARKET", "CL"),
            origin=os.getenv("ORIGIN", "SCL"),
            tokyo_codes=split_codes(os.getenv("TOKYO_CODES", "NRT,HND")),
            osaka_codes=split_codes(os.getenv("OSAKA_CODES", "KIX,ITM")),
            days_ahead=int(os.getenv("DAYS_AHEAD", "60")),
            stay_nights=int(os.getenv("STAY_NIGHTS", "14")),
            primary_currency=os.getenv("CURRENCY", "USD"),
            second_currency=os.getenv("SECOND_CURRENCY", "CLP"),
            fx_usdclp=os.getenv("FX_USDCLP"),
            departure_date_env=os.getenv("DEPARTURE_DATE", "").strip(),
            return_date_env=os.getenv("RETURN_DATE", "").strip(),
        )
