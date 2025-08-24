CREATE TABLE IF NOT EXISTS stock_prices (
  symbol      TEXT    NOT NULL,
  ts          DATE    NOT NULL,
  open        NUMERIC,
  high        NUMERIC,
  low         NUMERIC,
  close       NUMERIC,
  volume      BIGINT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (symbol, ts)
);

-- Keep updated_at fresh on upserts
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_updated_at ON stock_prices;
CREATE TRIGGER trg_set_updated_at
BEFORE UPDATE ON stock_prices
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();