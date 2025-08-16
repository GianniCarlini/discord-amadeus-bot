from .config import Settings


def get_settings() -> Settings:
    """
    Crea y retorna la configuración leída desde variables de entorno.
    Lanza ValueError si faltan credenciales obligatorias.
    """
    return Settings()


def main():
    settings = get_settings()

    print("Amadeus host:", settings.amadeus_host)
    print("Market:", settings.amadeus_market)
    print("Currency:", settings.amadeus_currency)
    print("Depart date (ENV):", settings.depart_date_env)
    print("Return date (ENV):", settings.return_date_env)
    print("ECHO_VERIFY:", settings.echo_verify)


if __name__ == "__main__":
    main()
