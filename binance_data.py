"""
binance_data.py
المسؤول عن سحب بيانات الشموع (Candles) والأسعار من Binance
"""

import time
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config


# عميل Binance - مش محتاج API Key/Secret لأننا هنسحب بيانات عامة بس (مش تنفيذ صفقات)
client = Client()


def get_klines(symbol: str, interval: str, limit: int = 250):
    """
    بيجيب الشموع (OHLCV) لعملة معينة على فريم زمني معين.
    بيرجع DataFrame فيه: الوقت، الفتح، الأعلى، الأدنى، القفل، الفوليوم
    بيرجع None لو حصل خطأ (رمز غلط، أو مشكلة اتصال)
    """
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    except BinanceAPIException as e:
        return None
    except Exception as e:
        return None

    if not klines:
        return None

    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    # تحويل الأعمدة المهمة لأرقام (بتيجي كنصوص من الـ API)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    return df


def get_last_closed_candle_df(symbol: str, interval: str, limit: int = 250):
    """
    زي get_klines بالظبط، بس بيشيل آخر شمعة لو لسه ماقفلتش
    (عشان منحسبش مؤشرات على بيانات ناقصة/بتتغير)
    """
    df = get_klines(symbol, interval, limit=limit)
    if df is None or len(df) < 2:
        return df

    # آخر شمعة ممكن تكون لسه بتتكون، فبنشيلها ونسيب اللي قبلها (المقفولة فعليًا)
    now_ms = int(time.time() * 1000)
    last_close_time_ms = int(df.iloc[-1]["close_time"].timestamp() * 1000)

    if last_close_time_ms > now_ms:
        df = df.iloc[:-1]

    return df


def has_enough_data(df) -> bool:
    """بيتأكد إن عندنا بيانات كفاية عشان نثق في المؤشرات (خصوصًا EMA200)"""
    if df is None:
        return False
    return len(df) >= config.MIN_CANDLES_REQUIRED


def detect_volatility_spike(df) -> bool:
    """
    بيكشف لو حصل تقلب مفاجئ (تحرك سعري كبير) في آخر ساعة
    بيرجع True لو التقلب أكبر من الحد المسموح في config
    """
    if df is None or len(df) < 5:
        return False

    recent = df.tail(4)  # آخر 4 شمعات (مثلاً لو 15m = آخر ساعة)
    price_change_pct = abs(
        (recent.iloc[-1]["close"] - recent.iloc[0]["close"]) / recent.iloc[0]["close"] * 100
    )
    return price_change_pct >= config.VOLATILITY_SPIKE_THRESHOLD


def get_top_volume_symbols(n: int = None, quote_asset: str = "USDT"):
    """
    بيجيب أعلى العملات فوليوم (تداول) مقابل USDT
    مستخدم في /scan عشان نفحص العملات الأكتر سيولة بس
    """
    if n is None:
        n = config.SCAN_TOP_N_COINS

    try:
        tickers = client.get_ticker()
    except Exception:
        return []

    # فلترة العملات اللي مقابل USDT بس، واستبعاد العملات المرفوعة (UP/DOWN) الغريبة
    usdt_pairs = [
        t for t in tickers
        if t["symbol"].endswith(quote_asset)
        and "UP" not in t["symbol"]
        and "DOWN" not in t["symbol"]
        and "BEAR" not in t["symbol"]
        and "BULL" not in t["symbol"]
    ]

    # ترتيب حسب حجم التداول (quoteVolume) تنازليًا
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)

    return [p["symbol"] for p in sorted_pairs[:n]]


def symbol_exists(symbol: str) -> bool:
    """بيتأكد إن رمز العملة ده موجود فعلاً على Binance قبل ما نحاول نحلله"""
    try:
        client.get_symbol_info(symbol)
        return True
    except Exception:
        return False
