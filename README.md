# Discord Amadeus Bot

app/
├─ __init__.py
├─ main.py                 # Punto de entrada (wire-up)
├─ bot_app.py              # Crea y configura el bot + scheduler + sync de slash
├─ commands.py             # Registro de comandos (/probar, /diag)
├─ flights_service.py      # Lógica de negocio (consultas y armado de mensajes)
├─ amadeus_client.py       # Cliente Amadeus (token + búsqueda ofertas)
├─ fx.py                   # Conversor de moneda (CLP, etc.) con cache
├─ config.py               # Carga de .env y settings tipados
├─ formatting.py           # Formateos y helpers de mensaje
└─ dates.py                # Parseo de fechas de env / cálculo por DAYS_AHEAD


Bot de Discord que, todos los días a las **11:00 America/Santiago**, publica en un canal:
1) Ofertas más baratas SCL ⇄ Tokio (NRT/HND)
2) Ofertas más baratas SCL ⇄ Osaka (KIX/ITM)

## Requisitos
- Python 3.12+
- Docker
- flyctl

## Configuración
1. Copia `.env.example` a `.env` y rellena variables.
2. (Local) Crea venv, instala deps y ejecuta:
   ```bash
   make venv
   make install
   make run

## Comandos
´/probar´
Publica de inmediato los 2 mensajes en el canal definido por DISCORD_CHANNEL_ID:

SCL ⇄ Tokio (NRT/HND)

SCL ⇄ Osaka (KIX/ITM)
Usa las fechas de DEPART_DATE/RETURN_DATE si están definidas; si no, calcula con DAYS_AHEAD y STAY_NIGHTS.

´/diag´
Muestra (solo para ti, ephemeral) un diagnóstico rápido: host de Amadeus, si ve las credenciales, moneda primaria/secundaria, fechas activas, CHANNEL_ID, GUILD_ID, etc.