import discord
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional


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
            f"TOKYO_CODES: {','.join(cfg.tokyo_codes)}\n"
            f"HOKKAIDO_CODES: {','.join(getattr(cfg, 'hokkaido_codes', []))}\n"
            f"SAPPORO_CODES: {','.join(getattr(cfg, 'sapporo_codes', []))}\n"
            f"JP_DOM_DEPART: {getattr(cfg, 'jp_dom_depart_env', None) or '(no set)'}\n"
            f"JP_DOM_RETURN: {getattr(cfg, 'jp_dom_return_env', None) or '(auto +1d)'}\n"
            f"CHANNEL_ID: {cfg.channel_id}\n"
            f"GUILD_ID: {cfg.guild_id}\n"
        )
        await interaction.response.send_message(f"```{msg}```", ephemeral=True)

    @tree.command(
        name="hokkaido",
        description="Tokio ⇄ Sapporo/Hakodate (puedes indicar fecha o usa variables de entorno)",
    )
    @app_commands.describe(
        departure="Fecha de salida (YYYY-MM-DD)",
        return_date="Fecha de regreso (YYYY-MM-DD, opcional; por defecto +1 día)",
    )
    async def hokkaido(
        interaction: discord.Interaction,
        departure: Optional[str] = None,
        return_date: Optional[str] = None,
    ):
        dep_str = departure or getattr(cfg, "jp_dom_depart_env", None)
        ret_str = return_date or getattr(cfg, "jp_dom_return_env", None)

        if not dep_str:
            await interaction.response.send_message(
                "❗ Debes pasar `departure` (YYYY-MM-DD) o configurar `JP_DOMESTIC_DEPART_DATE`.",
                ephemeral=True,
            )
            return

        try:
            d_dep = datetime.fromisoformat(dep_str).date()
        except Exception:
            await interaction.response.send_message("❗ `departure` inválida (usa YYYY-MM-DD).", ephemeral=True)
            return

        if ret_str:
            try:
                d_ret = datetime.fromisoformat(ret_str).date()
            except Exception:
                await interaction.response.send_message("❗ `return_date` inválida (usa YYYY-MM-DD).", ephemeral=True)
                return
            if d_ret <= d_dep:
                await interaction.response.send_message("❗ `return_date` debe ser posterior a `departure`.", ephemeral=True)
                return
        else:
            d_ret = d_dep + timedelta(days=1)

        await interaction.response.send_message("Enviando resultados al canal…", ephemeral=True)
        title = "✈️ Tokio ⇄ Hokkaidō (CTS/HKD) — Fecha seleccionada"
        msg = await flights_service.fetch_city_to_city_specific_dates(
            cfg.tokyo_codes,
            getattr(cfg, "hokkaido_codes", ["CTS", "HKD"]),
            title,
            d_dep.isoformat(),
            d_ret.isoformat(),
        )
        channel = bot.get_channel(cfg.channel_id)
        if channel: await channel.send(msg)
        else: await interaction.followup.send("❌ No pude encontrar el canal configurado.", ephemeral=True)

    @tree.command(
        name="sapporo",
        description="Tokio ⇄ Sapporo (puedes indicar fecha o usa variables de entorno)",
    )
    @app_commands.describe(
        departure="Fecha de salida (YYYY-MM-DD)",
        return_date="Fecha de regreso (YYYY-MM-DD, opcional; por defecto +1 día)",
    )
    async def sapporo(
        interaction: discord.Interaction,
        departure: Optional[str] = None,
        return_date: Optional[str] = None,
    ):
        dep_str = departure or getattr(cfg, "jp_dom_depart_env", None)
        ret_str = return_date or getattr(cfg, "jp_dom_return_env", None)

        if not dep_str:
            await interaction.response.send_message(
                "❗ Debes pasar `departure` (YYYY-MM-DD) o configurar `JP_DOMESTIC_DEPART_DATE`.",
                ephemeral=True,
            )
            return

        try:
            d_dep = datetime.fromisoformat(dep_str).date()
        except Exception:
            await interaction.response.send_message("❗ `departure` inválida (usa YYYY-MM-DD).", ephemeral=True)
            return

        if ret_str:
            try:
                d_ret = datetime.fromisoformat(ret_str).date()
            except Exception:
                await interaction.response.send_message("❗ `return_date` inválida (usa YYYY-MM-DD).", ephemeral=True)
                return
            if d_ret <= d_dep:
                await interaction.response.send_message("❗ `return_date` debe ser posterior a `departure`.", ephemeral=True)
                return
        else:
            d_ret = d_dep + timedelta(days=1)

        await interaction.response.send_message("Enviando resultados al canal…", ephemeral=True)
        title = "✈️ Tokio ⇄ Sapporo (CTS) — Fecha seleccionada"
        msg = await flights_service.fetch_city_to_city_specific_dates(
            cfg.tokyo_codes,
            getattr(cfg, "sapporo_codes", ["CTS"]),
            title,
            d_dep.isoformat(),
            d_ret.isoformat(),
        )
        channel = bot.get_channel(cfg.channel_id)
        if channel: await channel.send(msg)
        else: await interaction.followup.send("❌ No pude encontrar el canal configurado.", ephemeral=True)
