from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz

def parse_env_dates(dep_env: str, ret_env: str) -> Optional[Tuple[str, str]]:
    if not dep_env or not ret_env:
        return None
    try:
        d1 = datetime.fromisoformat(dep_env).date()
        d2 = datetime.fromisoformat(ret_env).date()
        if d1 >= d2:
            print("[WARN] RETURN_DATE debe ser posterior a DEPARTURE_DATE; se ignorarán fechas fijas.")
            return None
        return d1.isoformat(), d2.isoformat()
    except ValueError:
        print("[WARN] Formato inválido en DEPARTURE_DATE/RETURN_DATE (usa YYYY-MM-DD).")
        return None

def compute_dates(days_ahead: int, stay_nights: int, tz: pytz.timezone) -> Tuple[str, str]:
    today = datetime.now(tz)
    dpt = (today + timedelta(days=days_ahead)).date()
    rtn = dpt + timedelta(days=stay_nights)
    return dpt.isoformat(), rtn.isoformat()
