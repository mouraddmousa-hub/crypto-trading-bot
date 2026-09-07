"""
indicators.py
حساب المؤشرات الفنية: RSI, MACD, EMA, ودعم/مقاومة
"""

import pandas as pd
import config


def calculate_ema(df: pd.DataFrame, period: int, column: str = "close"):
    """حساب المتوسط المتحرك الأسي (EMA) لفترة معينة"""
    return df[column].ewm(span=period, adjust=False).mean()


def calculate_rsi(df: pd.DataFrame, period: int = None):
    """حساب مؤشر RSI"""
    if period is None:
        period = config.RSI_PERIOD

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(df: pd.DataFrame):
    """
    حساب MACD: بيرجع 3 قيم -> خط الماكد، خط الإشارة، والهيستوجرام
    """
    ema_fast = calculate_ema(df, config.MACD_FAST)
    ema_slow = calculate_ema(df, config.MACD_SLOW)

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=config.MACD_SIGNAL, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def find_support_resistance(df: pd.DataFrame, lookback: int = 50):
    """
    بيدور على أقرب مستوى دعم ومقاومة حقيقي
    عن طريق قمم وقيعان سعرية سابقة (آخر lookback شمعة)
    """
    recent = df.tail(lookback)

    resistance = recent["high"].max()
    support = recent["low"].min()

    return support, resistance


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    بتضيف كل المؤشرات كأعمدة جديدة في نفس الـ DataFrame
    عشان نقدر نستخدمهم بسهولة في ملف analysis.py
    """
    df = df.copy()

    df["ema_fast"] = calculate_ema(df, config.EMA_FAST)
    df["ema_slow"] = calculate_ema(df, config.EMA_SLOW)
    df["ema_trend_short"] = calculate_ema(df, config.EMA_TREND_SHORT)
    df["ema_trend_long"] = calculate_ema(df, config.EMA_TREND_LONG)

    df["rsi"] = calculate_rsi(df)

    macd_line, signal_line, histogram = calculate_macd(df)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_histogram"] = histogram

    return df


def get_trend_direction(df: pd.DataFrame) -> str:
    """
    بيحدد الاتجاه العام بناءً على السعر بالنسبة لـ EMA50 و EMA200
    بيرجع: "up" أو "down" أو "sideways"
    """
    last = df.iloc[-1]
    price = last["close"]
    ema50 = last["ema_trend_short"]
    ema200 = last["ema_trend_long"]

    if price > ema50 > ema200:
        return "up"
    elif price < ema50 < ema200:
        return "down"
    else:
        return "sideways"


def explain_rsi(rsi_value: float) -> str:
    """شرح بسيط لقيمة RSI بالعربي"""
    if rsi_value >= config.RSI_OVERBOUGHT:
        return f"RSI عند {rsi_value:.1f} - منطقة تشبع شرائي، السعر ممكن يكون مبالغ فيه صعودًا"
    elif rsi_value <= config.RSI_OVERSOLD:
        return f"RSI عند {rsi_value:.1f} - منطقة تشبع بيعي، السعر ممكن يكون مبالغ فيه هبوطًا"
    else:
        return f"RSI عند {rsi_value:.1f} - منطقة متعادلة، مفيش تشبع واضح"
