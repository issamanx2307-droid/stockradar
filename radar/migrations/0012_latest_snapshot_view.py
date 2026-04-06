"""
Migration 0012 — สร้าง Materialized View: radar_latest_snapshot

View นี้ join ข้อมูลล่าสุดจาก 4 ตาราง:
  radar_symbol      → ข้อมูลหุ้น
  radar_pricedaily  → ราคาล่าสุด (LATERAL JOIN)
  radar_indicator   → Indicator ล่าสุด (LATERAL JOIN)
  radar_signal      → Signal ล่าสุด (LATERAL JOIN)

Refresh: python manage.py refresh_snapshot
"""
from django.db import migrations, connection


def _is_postgres():
    return connection.vendor == "postgresql"


def create_view(apps, schema_editor):
    if not _is_postgres():
        return   # SQLite (test env) ไม่รองรับ MATERIALIZED VIEW
    schema_editor.execute(CREATE_VIEW)


def drop_view(apps, schema_editor):
    if not _is_postgres():
        return
    schema_editor.execute(DROP_VIEW)


CREATE_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS radar_latest_snapshot AS
SELECT
    s.id          AS symbol_id,
    s.symbol,
    s.name,
    s.exchange,
    s.sector,

    -- ─── ราคาล่าสุด ───────────────────────────────────────────────
    p.date        AS price_date,
    p.close,
    p.open,
    p.high,
    p.low,
    p.volume,

    -- ─── Technical Indicators ล่าสุด ──────────────────────────────
    i.ema20,
    i.ema50,
    i.ema200,
    i.rsi,
    i.macd,
    i.macd_signal,
    i.macd_hist,
    i.adx14,
    i.atr14,
    i.bb_upper,
    i.bb_lower,
    i.highest_high_20,
    i.lowest_low_20,
    i.volume_avg20,

    -- ─── Signal ล่าสุด ────────────────────────────────────────────
    sig.signal_type,
    sig.direction,
    sig.score       AS signal_score,
    sig.stop_loss,
    sig.risk_pct,
    sig.created_at  AS signal_date

FROM radar_symbol s

-- ราคาล่าสุด (1 แถวต่อหุ้น)
LEFT JOIN LATERAL (
    SELECT * FROM radar_pricedaily pd
    WHERE pd.symbol_id = s.id
    ORDER BY pd.date DESC
    LIMIT 1
) p ON true

-- Indicator ล่าสุด (1 แถวต่อหุ้น)
LEFT JOIN LATERAL (
    SELECT * FROM radar_indicator ind
    WHERE ind.symbol_id = s.id
    ORDER BY ind.date DESC
    LIMIT 1
) i ON true

-- Signal ล่าสุด คะแนนสูงสุด (1 แถวต่อหุ้น)
LEFT JOIN LATERAL (
    SELECT * FROM radar_signal sg
    WHERE sg.symbol_id = s.id
    ORDER BY sg.created_at DESC, sg.score DESC
    LIMIT 1
) sig ON true;

-- Index สำหรับ query เร็ว
CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshot_symbol_id
    ON radar_latest_snapshot (symbol_id);

CREATE INDEX IF NOT EXISTS idx_snapshot_score
    ON radar_latest_snapshot (signal_score DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_snapshot_exchange
    ON radar_latest_snapshot (exchange);

CREATE INDEX IF NOT EXISTS idx_snapshot_direction
    ON radar_latest_snapshot (direction);
"""

DROP_VIEW = """
DROP MATERIALIZED VIEW IF EXISTS radar_latest_snapshot CASCADE;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("radar", "0011_google_profile_fields"),
    ]

    operations = [
        migrations.RunPython(create_view, reverse_code=drop_view),
    ]
