import discord
from discord import app_commands
from datetime import datetime, timedelta

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
            f"DEPARTURE_DATE: {getattr(cfg, 'depart_date_env', None) or '(auto)'}\n"
            f"RETURN_DATE: {cfg.return_date_env or '(auto)'}\n"
            f"JP_DOM_DEPART: {getattr(cfg, 'jp_dom_depart_env', None) or '(no set)'}\n"
            f"JP_DOM_RETURN: {getattr(cfg, 'jp_dom_return_env', None) or '(auto +1d)'}\n"
            f"CHANNEL_ID: {cfg.channel_id}\n"
            f"GUILD_ID: {cfg.guild_id}\n"
        )
        await interaction.response.send_message(f"```{msg}```", ephemeral=True)

    @tree.command(name="hokkaido", description="Tokio ⇄ Sapporo/Hakodate (fecha fija desde variables de entorno)")
    async def hokkaido(interaction: discord.Interaction):
        dep = getattr(cfg, "jp_dom_depart_env", None)
        ret = getattr(cfg, "jp_dom_return_env", None)

        if not dep:
            await interaction.response.send_message(
                "❗ Configura `JP_DOMESTIC_DEPART_DATE` (YYYY-MM-DD) en las variables del servicio.",
                ephemeral=True,
            )
            return

        if not ret:
            try:
                d1 = datetime.fromisoformat(dep).date()
                ret = (d1 + timedelta(days=1)).isoformat()
            except Exception:
                await interaction.response.send_message("❗ `JP_DOMESTIC_DEPART_DATE` inválida (usa YYYY-MM-DD).", ephemeral=True)
                return

        await interaction.response.send_message("Enviando resultados al canal…", ephemeral=True)
        title = "✈️ Tokio ⇄ Hokkaidō (CTS/HKD) — Fecha fija"
        msg = await flights_service.fetch_city_to_city_specific_dates(
            cfg.tokyo_codes, cfg.hokkaido_codes, title, dep, ret
        )

        channel = bot.get_channel(cfg.channel_id)
        if channel:
            await channel.send(msg)
        else:
            await interaction.followup.send("❌ No pude encontrar el canal configurado.", ephemeral=True)
