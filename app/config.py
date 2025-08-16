from dataclasses import dataclass, field
from typing import Optional, List
import os
import pytz


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


def _split_csv(name: str, default: str = "") -> List[str]:
    raw = _env(name, default) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass
class Settings:
    # --- Discord ---
    token: str = field(default_factory=lambda: _env("DISCORD_TOKEN", ""))
    channel_id: int = field(default_factory=lambda: int((_env("DISCORD_CHANNEL_ID", "0") or "0")))
    guild_id: int = field(default_factory=lambda: int((_env("GUILD_ID", "0") or "0")))

    # --- Amadeus (requeridos) ---
    amadeus_host: str = field(default_factory=lambda: _env("AMADEUS_HOST", "https://test.api.amadeus.com"))
    amadeus_client_id: str = field(default_factory=lambda: _env("AMADEUS_CLIENT_ID", ""))
    amadeus_client_secret: str = field(default_factory=lambda: _env("AMADEUS_CLIENT_SECRET", ""))

    # --- Búsqueda (acepta nombres nuevos y antiguos) ---
    amadeus_market: str = field(default_factory=lambda: _env("AMADEUS_MARKET", _env("MARKET", "CL")) or "CL")
    amadeus_currency: str = field(default_factory=lambda: _env("AMADEUS_CURRENCY", _env("CURRENCY", "USD")) or "USD")
    origin: str = field(default_factory=lambda: _env("ORIGIN", "SCL"))
    tokyo_codes: List[str] = field(default_factory=lambda: _split_csv("TOKYO_CODES", "NRT,HND"))
    osaka_codes: List[str] = field(default_factory=lambda: _split_csv("OSAKA_CODES", "KIX,ITM"))
    days_ahead: int = field(default_factory=lambda: int(_env("DAYS_AHEAD", "60") or "60"))
    stay_nights: int = field(default_factory=lambda: int(_env("STAY_NIGHTS", "14") or "14"))
    max_results: int = field(default_factory=lambda: int(_env("MAX_RESULTS", "5") or "5"))

    # --- Monedas ---
    second_currency: str = field(default_factory=lambda: (_env("SECOND_CURRENCY", "CLP") or "CLP"))
    fx_usdclp: Optional[str] = field(default_factory=lambda: _env("FX_USDCLP"))

    # --- Fechas (nombres nuevos y antiguos) ---
    depart_date_env: Optional[str] = field(default_factory=lambda: _env("DEPART_DATE") or _env("DEPARTURE_DATE"))
    return_date_env: Optional[str] = field(default_factory=lambda: _env("RETURN_DATE"))

    # --- JAPÓN DOMÉSTICO ---
    hokkaido_codes: List[str] = field(default_factory=lambda: _split_csv("HOKKAIDO_CODES", "CTS,HKD"))
    jp_dom_depart_env: Optional[str] = field(default_factory=lambda: _env("JP_DOMESTIC_DEPART_DATE") or _env("JP_DOMESTIC_DATE"))
    jp_dom_return_env: Optional[str] = field(default_factory=lambda: _env("JP_DOMESTIC_RETURN_DATE"))
    okinawa_codes: List[str] = field(default_factory=lambda: _split_csv("OKINAWA_CODES", "OKA"))  # ← NUEVO

    # --- Otros ---
    timezone_str: str = field(default_factory=lambda: _env("TIMEZONE", "America/Santiago"))
    echo_verify: bool = field(default_factory=lambda: (_env("ECHO_VERIFY", "false") or "false").lower() in ("1", "true", "yes", "y"))

    def __post_init__(self):
        missing = []
        if not self.amadeus_client_id:
            missing.append("AMADEUS_CLIENT_ID")
        if not self.amadeus_client_secret:
            missing.append("AMADEUS_CLIENT_SECRET")
        if missing:
            raise ValueError("Faltan variables de entorno obligatorias: " + ", ".join(missing))

        self.amadeus_host = self.amadeus_host.rstrip("/")
        self.amadeus_market = (self.amadeus_market or "CL").upper()
        self.amadeus_currency = (self.amadeus_currency or "USD").upper()
        self.second_currency = (self.second_currency or "CLP").upper()

    # ---- Compatibilidad con el resto del código ----
    @property
    def market(self) -> str:
        return self.amadeus_market

    @property
    def primary_currency(self) -> str:
        return self.amadeus_currency

    @property
    def tz(self):
        return pytz.timezone(self.timezone_str)

    @property
    def departure_date_env(self) -> Optional[str]:
        return self.depart_date_env
