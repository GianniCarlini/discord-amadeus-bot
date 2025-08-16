from dataclasses import dataclass, field
import os
from typing import Optional


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Helper para leer variables de entorno con default opcional.
    """
    return os.getenv(name, default)


@dataclass
class Settings:
    amadeus_host: str = field(
        default_factory=lambda: _env("AMADEUS_HOST", "https://test.api.amadeus.com")
    )
    amadeus_client_id: str = field(
        default_factory=lambda: _env("AMADEUS_CLIENT_ID", "")
    )
    amadeus_client_secret: str = field(
        default_factory=lambda: _env("AMADEUS_CLIENT_SECRET", "")
    )

    amadeus_market: str = field(default_factory=lambda: _env("AMADEUS_MARKET", "CL"))
    amadeus_currency: str = field(default_factory=lambda: _env("AMADEUS_CURRENCY", "USD"))

    depart_date_env: Optional[str] = field(default_factory=lambda: _env("DEPART_DATE"))
    return_date_env: Optional[str] = field(default_factory=lambda: _env("RETURN_DATE"))

    echo_verify: bool = field(
        default_factory=lambda: _env("ECHO_VERIFY", "false").lower() in ("1", "true", "yes")
    )

    def __post_init__(self):
        """
        Valida requeridos y normaliza valores.
        """
        missing = []
        if not self.amadeus_client_id:
            missing.append("AMADEUS_CLIENT_ID")
        if not self.amadeus_client_secret:
            missing.append("AMADEUS_CLIENT_SECRET")

        if missing:
            raise ValueError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )

        self.amadeus_host = self.amadeus_host.rstrip("/")
        self.amadeus_market = (self.amadeus_market or "CL").upper()
        self.amadeus_currency = (self.amadeus_currency or "USD").upper()
