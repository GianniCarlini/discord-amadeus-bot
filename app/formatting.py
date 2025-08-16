from typing import Dict, Any, List, Optional

def format_clp(amount: float) -> str:
    return f"{int(round(amount)):,.0f}".replace(",", ".") + " CLP"

def fmt_offer(offer: Dict[str, Any], primary_currency: str, second_currency: Optional[str], rate: Optional[float]) -> str:
    price = offer.get("price", {})
    amount = float(price.get("grandTotal", "0") or 0)
    currency = (price.get("currency") or primary_currency).upper()

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
    primary_currency: str,
    second_currency: Optional[str],
    rate: Optional[float],
) -> str:
    if not offers:
        return f"**{title}**\n_No se encontraron ofertas para {origin}→{','.join(dests)} ({dep} / {ret})._"
    lines = [f"**{title}** _(salida {dep}, regreso {ret})_"]
    for o in offers:
        lines.append(fmt_offer(o, primary_currency, second_currency, rate))
    return "\n".join(lines)
