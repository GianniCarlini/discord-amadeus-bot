import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import aiohttp
import pytz

# Carga variables .env en local (en Railway usa Variables del proyecto)
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
CURRENCY = os.getenv("CURRENCY", "USD")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))

# Zona horaria Chile
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
        if self._token and self._token_exp and datetime.utcnow() < self._token_exp:
            return
        url = f"{self.host}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with session.post(url, data=data) as r:
            r.raise_for_status()
            js = await r.json()
            self._token = js["access_token"]
            self._token_exp = datetime.utcnow() + timedelta(
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


# ===== Helpers de fechas y formato =====
def compute_dates(days_ahead: int, stay_nights: int) -> (str, str):
    today = datetime.now(TZ)
    dpt = (today + timedelta(days=days_ahead)).date()
    rtn = dpt + timedelta(days=stay_nights)
    return dpt.isoformat(), rtn.isoformat()


def fmt_offer(offer: Dict[str, Any]) -> str:
    price = offer.get("price", {})
    amount = price.get("grandTotal", "?")
    currency = price.get("currency", CURRENCY)
    itin = (offer.get("itineraries") or [{}])[0]
    dur = itin.get("duration", "")
    segs = itin.get("segments", [])
    first = segs[0] if segs else {}
    last = segs[-1] if segs else {}
    dep = first.get("departure", {}).get("iataCode", "?")
    arr = last.get("arrival", {}).get("iataCode", "?")
    stops = max(0, len(segs) - 1)
    return f"• {dep}→{arr} | {stops} escala(s) | {dur} | {amount} {currency}"


def build_message(
    title: str, offers: List[Dict[str, Any]], origin: str, dests: List[str], dep: str, ret: str
) -> str:
    if not offers:
        return f"**{title}**\n_No se encontraron ofertas para {origin}→{','.join(dests)} ({dep} / {ret})._"
    lines = [f"**{title}** _(salida {dep}, regreso {ret})_"]
    for o in offers:
        lines.append(fmt_offer(o))
    return "\n".join(lines)


# ===== Búsqueda agregada por ciudad (múltiples aeropuertos) =====
async def fetch_cheapest_for_city_codes(dest_codes: List[str], title: str) -> str:
    dep, ret = compute_dates(DAYS_AHEAD, STAY_NIGHTS)
    aggregate: List[Dict[str, Any]] = []

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for code in dest_codes:
            try:
                offers = await amadeus.search_round_trip(
                    session,
                    origin=ORIGIN,
                    destination=code,
                    departure_date=dep,
                    return_date=ret,
                    currency=CURRENCY,
                    market=MARKET,
                    max_results=MAX_RESULTS,
                )
                aggregate.extend(offers)
            except Exception as e:
                # Log interno (no mostramos al usuario)
                print(f"[WARN] Dest {code} error: {e}")

    def price_total(o):
        try:
            return float(o["price"]["grandTotal"])
        except Exception:
            return 9e9

    aggregate.sort(key=price_total)
    top = aggregate[:MAX_RESULTS]
    return build_message(title, top, ORIGIN, dest_codes, dep, ret)


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

    # Programa tarea diaria a las 11:00 America/Santiago
    trigger = CronTrigger(hour=11, minute=0, timezone=TZ)
    for job in scheduler.get_jobs():
        scheduler.remove_job(job.id)
    scheduler.add_job(send_daily_messages, trigger, id="daily_flights")
    if not scheduler.running:
        scheduler.start()

    # Sincroniza slash commands (guild más rápido; global puede tardar minutos)
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
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
