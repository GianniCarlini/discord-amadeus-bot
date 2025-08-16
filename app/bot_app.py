import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Settings
from .commands import register_commands

def create_bot(cfg: Settings, flights_service):
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    scheduler = AsyncIOScheduler(timezone=cfg.tz)

    @bot.event
    async def on_ready():
        print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")

        # Cron diario 11:00 America/Santiago
        trigger = CronTrigger(hour=11, minute=0, timezone=cfg.tz)
        for job in scheduler.get_jobs():
            scheduler.remove_job(job.id)
        scheduler.add_job(flights_service.publish_daily, trigger, args=[bot], id="daily_flights")
        if not scheduler.running:
            scheduler.start()

        # Slash commands
        try:
            if cfg.guild_id:
                await bot.tree.sync(guild=discord.Object(id=cfg.guild_id))
                print("✅ Slash commands sincronizados en guild")
            else:
                await bot.tree.sync()
                print("✅ Slash commands sincronizados globalmente (puede tardar unos minutos)")
        except Exception as e:
            print(f"❌ Error sync: {e}")

    register_commands(bot, cfg, flights_service)
    return bot
