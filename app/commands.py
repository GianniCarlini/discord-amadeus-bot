import discord
from discord import app_commands

def register_commands(bot: discord.Client, cfg, flights_service):
    tree = bot.tree

    @tree.command(name="probar", description="Publica ahora los vuelos (Tokio y Osaka)")
    async def probar(interaction: discord.Interaction):
        await interaction.response.send_message("Enviando resultados al canal…", ephemeral=True)
        await flights_service.publish_daily(bot)

    @tree.command(name="diag", description="Diagnóstico rápido (sin exponer secretos)")
    async def diag(interaction: discord.Interaction):
        msg = (
            f"HOST: {cfg.amadeus_host}\n"
            f"CLIENT_ID_PRESENT: {bool(cfg.amadeus_client_id)}\n"
            f"SECRET_PRESENT: {bool(cfg.amadeus_client_secret)}\n"
            f"PRIMARY_CURRENCY: {cfg.primary_currency}\n"
            f"SECOND_CURRENCY: {cfg.second_currency}\n"
            f"DEPARTURE_DATE: {cfg.departure_date_env or '(auto)'}\n"
            f"RETURN_DATE: {cfg.return_date_env or '(auto)'}\n"
            f"CHANNEL_ID: {cfg.channel_id}\n"
            f"GUILD_ID: {cfg.guild_id}\n"
        )
        await interaction.response.send_message(f"```{msg}```", ephemeral=True)
