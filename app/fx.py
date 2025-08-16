from datetime import datetime, timedelta, UTC
from typing import Dict, Tuple, Optional
import aiohttp

class FXConverter:
    """Convierte montos entre monedas. Cache 12h. Permite override USD->CLP."""
    def __init__(self, usdclp_override: Optional[str] = None):
        self._cache: Dict[Tuple[str, str], Tuple[float, datetime]] = {}
        self._usdclp_override = usdclp_override

    async def get_rate(self, session: aiohttp.ClientSession, base: str, target: str) -> Optional[float]:
        base = base.upper()
        target = target.upper()
        if base == target:
            return 1.0

        key = (base, target)
        now = datetime.now(UTC)
        cached = self._cache.get(key)
        if cached:
            rate, exp = cached
            if now < exp:
                return rate

        if self._usdclp_override and base == "USD" and target == "CLP":
            try:
                rate = float(self._usdclp_override)
                self._cache[key] = (rate, now + timedelta(hours=12))
                return rate
            except ValueError:
                pass

        url = f"https://api.exchangerate.host/latest?base={base}&symbols={target}"
        try:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    print(f"[WARN] FX {base}->{target} status={r.status}")
                    return None
                js = await r.json()
                rate = float(js.get("rates", {}).get(target, 0))
                if rate > 0:
                    self._cache[key] = (rate, now + timedelta(hours=12))
                    return rate
                print(f"[WARN] FX {base}->{target} sin tasa válida")
                return None
        except Exception as e:
            print(f"[WARN] FX error: {e}")
            return None
