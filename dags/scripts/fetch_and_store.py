# dags/scripts/fetch_and_store.py
import os
import time
import logging
from typing import Dict, List, Iterable
import yfinance as yf # <-- NEW: Import yfinance
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- NEW DEBUGGING LINE ADDED HERE ---
log.warning("--- SCRIPT VERSION 3.0 (Yahoo Finance) IS RUNNING ---")

DATABASE_URL = os.environ["DATABASE_URL"]
# ALPHA_URL has been removed as it's no longer needed

# We are keeping this function the same
def upsert_rows(rows: Iterable[Dict]) -> int:
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


# --- THIS FUNCTION HAS BEEN COMPLETELY REWRITTEN FOR YFINANCE ---
def fetch_daily_data(symbol: str) -> List[Dict]:
    log.info("Fetching data for %s from Yahoo Finance", symbol)
    ticker = yf.Ticker(symbol)
    # Get historical market data for the last month
    hist_df = ticker.history(period="1mo")

    if hist_df.empty:
        log.warning("No data found for symbol %s", symbol)
        return []

    rows: List[Dict] = []
    # Loop through the DataFrame rows
    for date, row_data in hist_df.iterrows():
        rows.append({
            "symbol": symbol,
            "ts": date.strftime('%Y-%m-%d'), # Format date correctly
            "open": float(row_data["Open"]),
            "high": float(row_data["High"]),
            "low": float(row_data["Low"]),
            "close": float(row_data["Close"]),
            "volume": int(row_data["Volume"]),
        })
    return rows


# --- THIS FUNCTION HAS BEEN UPDATED TO CALL THE NEW FETCH FUNCTION ---
def run_once(symbols: List[str]):
    # No API key needed for yfinance
    for sym in symbols:
        try:
            log.info("Processing symbol: %s", sym)
            rows = fetch_daily_data(sym)
            log.info("For symbol %s, found %d rows of data from API.", sym, len(rows))
            if rows:
                count = upsert_rows(rows)
                log.info("%s: upserted %s rows", sym, count)
        except Exception as e:
            log.exception("Symbol %s failed: %s", sym, e)

if __name__ == "__main__":
    symbols = [s.strip().upper() for s in os.getenv("SYMBOLS", "AAPL").split(",") if s.strip()]
    run_once(symbols)