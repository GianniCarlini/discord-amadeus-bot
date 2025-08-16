from dotenv import load_dotenv
load_dotenv()

from .config import Settings
from .amadeus_client import AmadeusClient
from .fx import FXConverter
from .flights_service import FlightsService
from .bot_app import create_bot

def main():
    cfg = Settings()
    if not cfg.token or cfg.channel_id == 0:
        raise RuntimeError("Faltan DISCORD_TOKEN o DISCORD_CHANNEL_ID")

    amadeus = AmadeusClient(cfg.amadeus_host, cfg.amadeus_client_id, cfg.amadeus_client_secret)
    fx = FXConverter(usdclp_override=cfg.fx_usdclp)
    flights_service = FlightsService(cfg, amadeus, fx)

    print(f"[DIAG] PRIMARY={cfg.primary_currency}, SECOND={cfg.second_currency}, "
          f"DEP={cfg.depart_date_env or '(auto)'} RET={cfg.return_date_env or '(auto)'}")

    bot = create_bot(cfg, flights_service)
    bot.run(cfg.token)

if __name__ == "__main__":
    main()
