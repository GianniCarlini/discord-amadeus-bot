from datetime import datetime, timedelta, UTC
from typing import Dict, Tuple, Optional
import aiohttp

DINERO_TODAY_URL = "https://cdn.dinero.today/api/latest.json"


class FXConverter:
    """
    Convierte montos entre monedas, con cache de 12h.
    Prioriza dinero.today; si falla, usa exchangerate.host.
    Permite override USD->CLP via FX_USDCLP.
    """
    def __init__(self, usdclp_override: Optional[str] = None, cache_hours: int = 12):
        self._cache: Dict[Tuple[str, str], Tuple[float, datetime]] = {}
        self._usdclp_override = usdclp_override
        self._cache_ttl = timedelta(hours=cache_hours)

    async def _from_dinero_today(self, session: aiohttp.ClientSession, base: str, target: str) -> Optional[float]:
        """
        dinero.today expone rates con BASE=USD en latest.json:
        - rate(USD->X) = rates[X]
        - rate(X->USD) = 1 / rates[X]
        - rate(A->B) = rates[B] / rates[A]
        """
        try:
            async with session.get(DINERO_TODAY_URL, timeout=10) as r:
                if r.status != 200:
                    return None
                js = await r.json()
            rates = js.get("rates", {})
            if not isinstance(rates, dict):
                return None

            if base == "USD":
                val = rates.get(target)
                return float(val) if val else None
            if target == "USD":
                val = rates.get(base)
                return (1.0 / float(val)) if val else None

            t_val = rates.get(target)
            b_val = rates.get(base)
            if t_val and b_val:
                return float(t_val) / float(b_val)

            return None
        except Exception as e:
            print(f"[WARN] FX dinero.today error: {e}")
            return None

    async def _from_exchangerate_host(self, session: aiohttp.ClientSession, base: str, target: str) -> Optional[float]:
        url = f"https://api.exchangerate.host/latest?base={base}&symbols={target}"
        try:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    print(f"[WARN] FX {base}->{target} status={r.status}")
                    return None
                js = await r.json()
                rate = js.get("rates", {}).get(target)
                return float(rate) if rate else None
        except Exception as e:
            print(f"[WARN] FX exchangerate.host error: {e}")
            return None

    async def get_rate(self, session: aiohttp.ClientSession, base: str, target: str) -> Optional[float]:
        base = base.upper()
        target = target.upper()
        if base == target:
            return 1.0

        key = (base, target)
        now = datetime.now(UTC)
        cached = self._cache.get(key)
        if cached and now < cached[1]:
            return cached[0]

        if self._usdclp_override and base == "USD" and target == "CLP":
            try:
                rate = float(self._usdclp_override)
                self._cache[key] = (rate, now + self._cache_ttl)
                return rate
            except ValueError:
                pass

        rate = await self._from_dinero_today(session, base, target)
        if rate and rate > 0:
            self._cache[key] = (rate, now + self._cache_ttl)
            return rate

        rate = await self._from_exchangerate_host(session, base, target)
        if rate and rate > 0:
            self._cache[key] = (rate, now + self._cache_ttl)
            return rate

        print(f"[WARN] FX no rate for {base}->{target}")
        return None
