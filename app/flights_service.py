from typing import List, Dict, Any, Optional
import aiohttp

from .config import Settings
from .amadeus_client import AmadeusClient
from .fx import FXConverter
from .formatting import build_message
from .dates import parse_env_dates, compute_dates


class FlightsService:
    def __init__(self, cfg: Settings, amadeus: AmadeusClient, fx: FXConverter):
        self.cfg = cfg
        self.amadeus = amadeus
        self.fx = fx

    async def _fetch_city_codes(self, dest_codes: List[str], title: str) -> str:
        dep_env = getattr(self.cfg, "depart_date_env", None)
        ret_env = getattr(self.cfg, "return_date_env", None)
        env_dates = parse_env_dates(dep_env, ret_env)

        if env_dates:
            dep, ret = env_dates
        else:
            dep, ret = compute_dates(self.cfg.days_ahead, self.cfg.stay_nights, self.cfg.tz)

        aggregate: List[Dict[str, Any]] = []
        rate: Optional[float] = None

        timeout = aiohttp.ClientTimeout(total=35)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for code in dest_codes:
                try:
                    offers = await self.amadeus.search_round_trip(
                        session,
                        origin=self.cfg.origin,
                        destination=code,
                        departure_date=dep,
                        return_date=ret,
                        currency=self.cfg.primary_currency,
                        market=self.cfg.market,
                        max_results=self.cfg.max_results,
                    )
                    aggregate.extend(offers)

                    if rate is None and offers and self.cfg.second_currency:
                        offer_ccy = (offers[0].get("price", {}).get("currency") or self.cfg.primary_currency).upper()
                        rate = await self.fx.get_rate(session, offer_ccy, self.cfg.second_currency.upper())
                except Exception as e:
                    print(f"[WARN] Dest {code} error: {e}")

        def price_total(o: Dict[str, Any]) -> float:
            try:
                return float(o["price"]["grandTotal"])
            except Exception:
                return 9e9

        aggregate.sort(key=price_total)
        top = aggregate[: self.cfg.max_results]

        return build_message(
            title=title,
            offers=top,
            origin=self.cfg.origin,
            dests=dest_codes,
            dep=dep,
            ret=ret,
            primary_currency=self.cfg.primary_currency,
            second_currency=self.cfg.second_currency,
            rate=rate,
        )

    async def fetch_city_to_city_specific_dates(
        self,
        origin_codes: List[str],
        dest_codes: List[str],
        title: str,
        dep: str,
        ret: str,
    ) -> str:
        """Consulta combinando varios orígenes y destinos para fechas fijas."""
        aggregate: List[Dict[str, Any]] = []
        rate: Optional[float] = None

        timeout = aiohttp.ClientTimeout(total=35)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for o_code in origin_codes:
                for d_code in dest_codes:
                    try:
                        offers = await self.amadeus.search_round_trip(
                            session,
                            origin=o_code,
                            destination=d_code,
                            departure_date=dep,
                            return_date=ret,
                            currency=self.cfg.primary_currency,
                            market=self.cfg.market,
                            max_results=self.cfg.max_results,
                        )
                        aggregate.extend(offers)

                        if rate is None and offers and self.cfg.second_currency:
                            offer_ccy = (offers[0].get("price", {}).get("currency") or self.cfg.primary_currency).upper()
                            rate = await self.fx.get_rate(session, offer_ccy, self.cfg.second_currency.upper())
                    except Exception as e:
                        print(f"[WARN] {o_code}->{d_code} error: {e}")

        def price_total(o: Dict[str, Any]) -> float:
            try:
                return float(o["price"]["grandTotal"])
            except Exception:
                return 9e9

        aggregate.sort(key=price_total)
        top = aggregate[: self.cfg.max_results]

        origin_label = "/".join(origin_codes)
        dest_label = "/".join(dest_codes)

        return build_message(
            title=title,
            offers=top,
            origin=origin_label,
            dests=[dest_label],
            dep=dep,
            ret=ret,
            primary_currency=self.cfg.primary_currency,
            second_currency=self.cfg.second_currency,
            rate=rate,
        )

    async def publish_daily(self, bot) -> None:
        channel = bot.get_channel(self.cfg.channel_id)
        if channel is None:
            print("❌ Canal no encontrado. Revisa DISCORD_CHANNEL_ID.")
            return

        msg_tokyo = await self._fetch_city_codes(
            self.cfg.tokyo_codes, "✈️ SCL ⇄ Tokio (NRT/HND) — Ofertas más baratas"
        )
        msg_osaka = await self._fetch_city_codes(
            self.cfg.osaka_codes, "✈️ SCL ⇄ Osaka (KIX/ITM) — Ofertas más baratas"
        )

        await channel.send(msg_tokyo)
        await channel.send(msg_osaka)
