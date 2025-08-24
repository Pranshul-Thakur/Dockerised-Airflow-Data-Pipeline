# dags/scripts/fetch_and_store.py
import os
import time
import logging
from typing import Dict, List, Iterable
import requests
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATABASE_URL = os.environ["DATABASE_URL"]
ALPHA_URL = "https://www.alphavantage.co/query"

def _request_with_retries(params: Dict[str, str], retries: int = 5, backoff: float = 1.5) -> Dict:
    # ... (the rest of your function is fine)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(ALPHA_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "Note" in data:
                raise RuntimeError(f"API limit/throttle: {data['Note']}")
            if "Error Message" in data:
                raise RuntimeError(data["Error Message"])
            return data
        except Exception as e:
            wait = backoff ** attempt
            log.warning("Attempt %s/%s failed: %s — retrying in %.1fs", attempt, retries, e, wait)
            if attempt == retries:
                raise
            time.sleep(wait)

def fetch_daily_adjusted(symbol: str, api_key: str) -> List[Dict]:
    # ... (this function is fine)
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "apikey": api_key,
        "outputsize": "compact",
        "datatype": "json",
    }
    payload = _request_with_retries(params)
    ts_key = next((k for k in payload.keys() if k.lower().startswith("time series")), None)
    if not ts_key or ts_key not in payload:
        raise ValueError(f"Unexpected response structure for {symbol}")
    series = payload[ts_key]
    rows: List[Dict] = []
    for date_str, vals in series.items():
        try:
            rows.append({
                "symbol": symbol,
                "ts": date_str,
                "open": float(vals.get("1. open") or 0.0),
                "high": float(vals.get("2. high") or 0.0),
                "low": float(vals.get("3. low") or 0.0),
                "close": float(vals.get("4. close") or 0.0),
                "volume": int(vals.get("6. volume") or 0),
            })
        except Exception as e:
            log.warning("Skipping malformed row for %s on %s: %s", symbol, date_str, e)
    return rows

def upsert_rows(rows: Iterable[Dict]) -> int:
    # ... (this function is fine)
    if not rows:
        return 0
    engine = create_engine(DATABASE_URL, future=True)
    sql = text("""
        INSERT INTO stock_prices (symbol, ts, open, high, low, close, volume)
        VALUES (:symbol, :ts, :open, :high, :low, :close, :volume)
        ON CONFLICT (symbol, ts)
        DO UPDATE SET
          open = EXCLUDED.open,
          high = EXCLUDED.high,
          low  = EXCLUDED.low,
          close= EXCLUDED.close,
          volume = EXCLUDED.volume,
          updated_at = NOW();
    """)
    with engine.begin() as conn:
        for row in rows:
            try:
                conn.execute(sql, row)
            except Exception as e:
                log.error("Upsert failed for %s %s: %s", row.get("symbol"), row.get("ts"), e)
    return len(list(rows))

def run_once(symbols: List[str]): # <-- Use capital L here
    # ... (this function is fine)
    api_key = os.environ["ALPHAVANTAGE_API_KEY"]
    for sym in symbols:
        try:
            log.info("Fetching %s", sym)
            rows = fetch_daily_adjusted(sym, api_key)
            count = upsert_rows(rows)
            log.info("%s: upserted %s rows", sym, count)
        except Exception as e:
            log.exception("Symbol %s failed: %s", sym, e)

if __name__ == "__main__":
    symbols = [s.strip().upper() for s in os.getenv("SYMBOLS", "AAPL").split(",") if s.strip()]
    run_once(symbols)