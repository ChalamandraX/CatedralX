"""BTC/gold ratio from caller-supplied observed prices."""
import math

def ratio_btc_oro(precio_btc: float, precio_oro: float) -> dict:
    btc, oro = float(precio_btc), float(precio_oro)
    if not all(math.isfinite(x) and x > 0 for x in (btc, oro)):
        raise ValueError("both observed prices must be positive and finite")
    return {"ratio": round(btc / oro, 8), "btc_price": btc, "gold_price": oro,
            "source": "caller_supplied", "analysis_only": True}
