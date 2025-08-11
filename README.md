# Discord Amadeus Bot

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
