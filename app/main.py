import os
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import aiohttp
import pytz

load_dotenv()

# ===== Config Discord =====
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # opcional para sync inmediato de slash

# ===== Config Amadeus / búsqueda =====
AMADEUS_HOST = os.getenv("AMADEUS_HOST", "https://test.api.amadeus.com")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

MARKET = os.getenv("MARKET", "CL")
ORIGIN = os.getenv("ORIGIN", "SCL")
TOKYO_CODES = os.getenv("TOKYO_CODES", "NRT,HND").split(",")
OSAKA_CODES = os.getenv("OSAKA_CODES", "KIX,ITM").split(",")
DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "60"))
STAY_NIGHTS = int(os.getenv("STAY_NIGHTS", "14"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))

# Monedas: primaria (en la que consulta Amadeus) y secundaria para mostrar equivalencia
PRIMARY_CURRENCY = os.getenv("CURRENCY", "USD")  # precio principal (p.ej. USD)
SECOND_CURRENCY = os.getenv("SECOND_CURRENCY", "CLP")  # equivalencia a mostrar (p.ej. CLP)

# Fechas fijas opcionales (YYYY-MM-DD). Si no están, usa DAYS_AHEAD/STAY_NIGHTS.
DEPARTURE_DATE_ENV = os.getenv("DEPARTURE_DATE", "").strip()
RETURN_DATE_ENV = os.getenv("RETURN_DATE", "").strip()

# FX manual opcional
FX_USDCLP = os.getenv("FX_USDCLP")

TZ = pytz.timezone("America/Santiago")

# ===== Discord Bot =====
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
scheduler = AsyncIOScheduler(timezone=TZ)


# ===== Cliente Amadeus =====
class AmadeusClient:
    def __init__(self, host: str, client_id: str, client_secret: str):
        self.host = host.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_exp: Optional[datetime] = None

    async def _ensure_token(self, session: aiohttp.ClientSession):
        """Obtiene/refresca el token OAuth2 si está ausente o expirado."""
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
        """Busca ofertas ida/vuelta usando /v2/shopping/flight-offers."""
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


amadeus = AmadeusClient(AMADEUS_HOST, AMADEUS_CLIENT_ID, AMADEUS_CLIENT_SECRET)


# ===== FX Converter =====
class FXConverter:
    def __init__(self):
        self._cache: Dict[Tuple[str, str], Tuple[float, datetime]] = {}

    async def get_rate(self, session: aiohttp.ClientSession, base: str, target: str) -> Optional[float]:
        base = base.upper()
        target = target.upper()
        if base == target:
            return 1.0

        key = (base, target)
        cached = self._cache.get(key)
        now = datetime.now(UTC)
        if cached:
            rate, exp = cached
            if now < exp:
                return rate

        if FX_USDCLP and base == "USD" and target == "CLP":
            try:
                rate = float(FX_USDCLP)
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


fx = FXConverter()


# ===== Helpers de fechas y formato =====
def parse_env_dates() -> Optional[Tuple[str, str]]:
    if not DEPARTURE_DATE_ENV or not RETURN_DATE_ENV:
        return None
    try:
        d1 = datetime.fromisoformat(DEPARTURE_DATE_ENV).date()
        d2 = datetime.fromisoformat(RETURN_DATE_ENV).date()
        if d1 >= d2:
            print("[WARN] RETURN_DATE debe ser posterior a DEPARTURE_DATE; se ignorarán fechas fijas.")
            return None
        return d1.isoformat(), d2.isoformat()
    except ValueError:
        print("[WARN] Formato inválido en DEPARTURE_DATE/RETURN_DATE (usa YYYY-MM-DD).")
        return None


def compute_dates(days_ahead: int, stay_nights: int) -> Tuple[str, str]:
    today = datetime.now(TZ)
    dpt = (today + timedelta(days=days_ahead)).date()
    rtn = dpt + timedelta(days=stay_nights)
    return dpt.isoformat(), rtn.isoformat()


def format_usd(amount: float) -> str:
    return f"{amount:,.2f} USD"


def format_clp(amount: float) -> str:
    return f"{int(round(amount)):,.0f}".replace(",", ".") + " CLP"


def fmt_offer(offer: Dict[str, Any], second_currency: Optional[str], rate: Optional[float]) -> str:
    price = offer.get("price", {})
    amount = float(price.get("grandTotal", "0") or 0)
    currency = (price.get("currency") or PRIMARY_CURRENCY).upper()

    itin = (offer.get("itineraries") or [{}])[0]
    dur = itin.get("duration", "")
    segs = itin.get("segments", [])
    first = segs[0] if segs else {}
    last = segs[-1] if segs else {}
    dep = first.get("departure", {}).get("iataCode", "?")
    arr = last.get("arrival", {}).get("iataCode", "?")
    stops = max(0, len(segs) - 1)

    primary_str = f"{amount:,.2f} {currency}"
    line = f"• {dep}→{arr} | {stops} escala(s) | {dur} | {primary_str}"

    if second_currency and rate and amount > 0:
        eq = amount * rate
        if second_currency.upper() == "CLP":
            line += f" (≈ {format_clp(eq)})"
        else:
            line += f" (≈ {eq:,.2f} {second_currency.upper()})"
    return line


def build_message(
    title: str,
    offers: List[Dict[str, Any]],
    origin: str,
    dests: List[str],
    dep: str,
    ret: str,
    second_currency: Optional[str],
    rate: Optional[float],
) -> str:
    if not offers:
        return f"**{title}**\n_No se encontraron ofertas para {origin}→{','.join(dests)} ({dep} / {ret})._"
    header = f"**{title}** _(salida {dep}, regreso {ret})_"
    lines = [header]
    for o in offers:
        lines.append(fmt_offer(o, second_currency, rate))
    return "\n".join(lines)


# ===== Búsqueda agregada por ciudad (múltiples aeropuertos) =====
async def fetch_cheapest_for_city_codes(dest_codes: List[str], title: str) -> str:
    env_dates = parse_env_dates()
    if env_dates:
        dep, ret = env_dates
    else:
        dep, ret = compute_dates(DAYS_AHEAD, STAY_NIGHTS)

    aggregate: List[Dict[str, Any]] = []

    timeout = aiohttp.ClientTimeout(total=35)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        rate: Optional[float] = None

        for idx, code in enumerate(dest_codes):
            try:
                offers = await amadeus.search_round_trip(
                    session,
                    origin=ORIGIN,
                    destination=code,
                    departure_date=dep,
                    return_date=ret,
                    currency=PRIMARY_CURRENCY,
                    market=MARKET,
                    max_results=MAX_RESULTS,
                )
                aggregate.extend(offers)

                if rate is None and offers:
                    offer_ccy = (offers[0].get("price", {}).get("currency") or PRIMARY_CURRENCY).upper()
                    if SECOND_CURRENCY:
                        rate = await fx.get_rate(session, offer_ccy, SECOND_CURRENCY.upper())
            except Exception as e:
                print(f"[WARN] Dest {code} error: {e}")

    def price_total(o):
        try:
            return float(o["price"]["grandTotal"])
        except Exception:
            return 9e9

    aggregate.sort(key=price_total)
    top = aggregate[:MAX_RESULTS]
    return build_message(title, top, ORIGIN, dest_codes, dep, ret, SECOND_CURRENCY, rate)


# ===== Publicación de mensajes diarios =====
async def send_daily_messages():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("❌ Canal no encontrado. Revisa DISCORD_CHANNEL_ID.")
        return

    # 1) SCL → Tokio (NRT/HND)
    msg_tokyo = await fetch_cheapest_for_city_codes(
        TOKYO_CODES, "✈️ SCL ⇄ Tokio (NRT/HND) — Ofertas más baratas"
    )

    # 2) SCL → Osaka (KIX/ITM)
    msg_osaka = await fetch_cheapest_for_city_codes(
        OSAKA_CODES, "✈️ SCL ⇄ Osaka (KIX/ITM) — Ofertas más baratas"
    )

    await channel.send(msg_tokyo)
    await channel.send(msg_osaka)


# ===== Slash command para probar sin esperar el cron =====
@tree.command(name="probar", description="Publica ahora los vuelos (Tokio y Osaka)")
async def probar(interaction: discord.Interaction):
    await interaction.response.send_message("Enviando resultados al canal…", ephemeral=True)
    await send_daily_messages()


# ===== Eventos del bot =====
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")

    trigger = CronTrigger(hour=11, minute=0, timezone=TZ)
    for job in scheduler.get_jobs():
        scheduler.remove_job(job.id)
    scheduler.add_job(send_daily_messages, trigger, id="daily_flights")
    if not scheduler.running:
        scheduler.start()

    try:
        if GUILD_ID:
            await tree.sync(guild=discord.Object(id=GUILD_ID))
            print("✅ Slash commands sincronizados en guild")
        else:
            await tree.sync()
            print("✅ Slash commands sincronizados globalmente (puede tardar unos minutos)")
    except Exception as e:
        print(f"❌ Error sync: {e}")


def main():
    if not TOKEN or CHANNEL_ID == 0:
        raise RuntimeError("Faltan DISCORD_TOKEN o DISCORD_CHANNEL_ID")
    print(f"[DIAG] PRIMARY_CURRENCY={PRIMARY_CURRENCY}, SECOND_CURRENCY={SECOND_CURRENCY}, "
          f"DEPARTURE_DATE={DEPARTURE_DATE_ENV or '(auto)'}, RETURN_DATE={RETURN_DATE_ENV or '(auto)'}")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
