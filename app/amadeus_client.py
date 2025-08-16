from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional
import aiohttp

class AmadeusClient:
    def __init__(self, host: str, client_id: Optional[str], client_secret: Optional[str]):
        self.host = host.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_exp: Optional[datetime] = None

    async def _ensure_token(self, session: aiohttp.ClientSession):
        if self._token and self._token_exp and datetime.now(UTC) < self._token_exp:
            return
        url = f"{self.host}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id or "",
            "client_secret": self.client_secret or "",
        }
        async with session.post(url, data=data, headers=headers) as r:
            text = await r.text()
            if r.status != 200:
                print(f"[ERR] Token fail {r.status}: {text[:300]}")
                raise RuntimeError(f"Amadeus token {r.status}")
            js = await r.json()
            self._token = js["access_token"]
            self._token_exp = datetime.now(UTC) + timedelta(
                seconds=int(js.get("expires_in", 1800)) - 60
            )

    async def search_round_trip(
        self,
        session: aiohttp.ClientSession,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        currency: str = "USD",
        market: str = "CL",
        adults: int = 1,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        await self._ensure_token(session)
        url = f"{self.host}/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {self._token}"}
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": str(adults),
            "currencyCode": currency,
            "max": str(max_results),
            "nonStop": "false",
        }
        async with session.get(url, headers=headers, params=params) as r:
            if r.status != 200:
                text = await r.text()
                raise RuntimeError(f"Amadeus {r.status}: {text}")
            data = await r.json()
            offers = data.get("data", [])
            def price_total(o):
                try:
                    return float(o["price"]["grandTotal"])
                except Exception:
                    return 9e9
            offers.sort(key=price_total)
            return offers[:max_results]
