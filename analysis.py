"""
analysis.py
دماغ البوت - بيقرر هل فيه صفقة ولا لأ، ونوعها، وتفاصيلها
"""

import config
import binance_data
import indicators


class TradeSignal:
    """كائن بسيط بيشيل كل تفاصيل الصفقة المقترحة"""

    def __init__(self, symbol, trade_type, direction, entry, stop_loss,
                 target1, target2, risk_reward, reason, is_weak=False):
        self.symbol = symbol
        self.trade_type = trade_type      # "scalp" أو "swing"
        self.direction = direction        # "buy" أو "sell"
        self.entry = entry
        self.stop_loss = stop_loss
        self.target1 = target1
        self.target2 = target2
        self.risk_reward = risk_reward
        self.reason = reason              # شرح مختصر ليه اتاخد القرار ده (لـ /explain)
        self.is_weak = is_weak            # لو الصفقة ضعيفة/مخاطرتها عالية


def analyze_symbol(symbol: str, market_type: str = "spot"):
    """
    التحليل الكامل لعملة واحدة.
    بيرجع (TradeSignal, error_message)
    - لو فيه صفقة: TradeSignal بالتفاصيل، error_message = None
    - لو مفيش صفقة قوية بس فيه فرصة ضعيفة: TradeSignal بـ is_weak=True
    - لو مفيش حاجة خالص أو حصل مشكلة: TradeSignal = None، error_message فيها السبب
    """

    # 1. التأكد إن العملة موجودة أصلاً
    if not binance_data.symbol_exists(symbol):
        return None, f"العملة {symbol} مش موجودة على Binance، تأكد من الرمز"

    # 2. جيب بيانات الفريم الكبير (الاتجاه العام)
    trend_df = binance_data.get_last_closed_candle_df(
        symbol, config.TREND_TIMEFRAME, limit=250
    )

    if not binance_data.has_enough_data(trend_df):
        return None, f"بيانات {symbol} غير كافية لتحليل موثوق (العملة جديدة أو حديثة الإدراج)"

    # 3. تحقق من التقلب المفاجئ
    if binance_data.detect_volatility_spike(trend_df):
        return None, f"{symbol} في حالة تقلب سعري حاد حاليًا، التحليل العادي مش موثوق دلوقتي"

    trend_df = indicators.add_all_indicators(trend_df)
    trend_direction = indicators.get_trend_direction(trend_df)

    # 4. جرب سكالب الأول
    scalp_signal = _try_scalp(symbol, trend_direction, trend_df)
    if scalp_signal and not scalp_signal.is_weak:
        return scalp_signal, None

    # 5. لو السكالب مفيش، جرب سوينج
    swing_signal = _try_swing(symbol, trend_direction, trend_df)
    if swing_signal and not swing_signal.is_weak:
        return swing_signal, None

    # 6. مفيش صفقة قوية - ارجع أقرب فرصة متاحة (سكالب أو سوينج) حتى لو ضعيفة
    weak_candidate = scalp_signal or swing_signal
    if weak_candidate:
        return weak_candidate, None

    return None, f"مفيش فرصة تداول متاحة على {symbol} دلوقتي"


def _try_scalp(symbol, trend_direction, trend_df):
    """محاولة إيجاد صفقة سكالبينج على فريم 15m متوافقة مع الاتجاه العام"""
    entry_df = binance_data.get_last_closed_candle_df(
        symbol, config.ENTRY_TIMEFRAME_SCALP, limit=250
    )
    if not binance_data.has_enough_data(entry_df):
        return None

    entry_df = indicators.add_all_indicators(entry_df)
    last = entry_df.iloc[-1]

    support, resistance = indicators.find_support_resistance(entry_df, lookback=50)

    # قاعدة: الفريم الكبير هو الحاكم - منتاجرش عكس الاتجاه العام
    if trend_direction == "up":
        direction = "buy"
    elif trend_direction == "down":
        direction = "sell"
    else:
        return None  # اتجاه عرضي = مفيش سكالب واضح

    # شرط الدخول: اختراق EMA سريع/بطيء + فوليوم أعلى من المتوسط
    avg_volume = entry_df["volume"].tail(20).mean()
    volume_ok = last["volume"] > avg_volume

    ema_cross_up = last["ema_fast"] > last["ema_slow"]
    ema_cross_down = last["ema_fast"] < last["ema_slow"]

    signal_valid = (direction == "buy" and ema_cross_up and volume_ok) or \
                   (direction == "sell" and ema_cross_down and volume_ok)

    entry_price = last["close"]
    buffer = config.STOP_LOSS_BUFFER_PERCENT / 100

    if direction == "buy":
        stop_loss = support * (1 - buffer)
        risk = entry_price - stop_loss
        target1 = entry_price + risk * config.MIN_RISK_REWARD_SCALP
        target2 = entry_price + risk * (config.MIN_RISK_REWARD_SCALP + 1)
    else:
        stop_loss = resistance * (1 + buffer)
        risk = stop_loss - entry_price
        target1 = entry_price - risk * config.MIN_RISK_REWARD_SCALP
        target2 = entry_price - risk * (config.MIN_RISK_REWARD_SCALP + 1)

    if risk <= 0:
        return None

    reward = abs(target1 - entry_price)
    risk_reward = reward / risk if risk > 0 else 0

    reason = (
        f"الاتجاه العام على فريم {config.TREND_TIMEFRAME} كان {trend_direction}. "
        f"على فريم {config.ENTRY_TIMEFRAME_SCALP}: "
        f"{'اختراق EMA9 فوق EMA21' if direction == 'buy' else 'كسر EMA9 تحت EMA21'} "
        f"مع فوليوم {'أعلى' if volume_ok else 'أقل'} من المتوسط. "
        f"{indicators.explain_rsi(last['rsi'])}"
    )

    is_weak = not (signal_valid and risk_reward >= config.MIN_RISK_REWARD_SCALP)

    return TradeSignal(
        symbol=symbol, trade_type="scalp", direction=direction,
        entry=entry_price, stop_loss=stop_loss,
        target1=target1, target2=target2,
        risk_reward=risk_reward, reason=reason, is_weak=is_weak
    )


def _try_swing(symbol, trend_direction, trend_df):
    """محاولة إيجاد صفقة سوينج على فريم يومي متوافقة مع الاتجاه العام"""
    entry_df = binance_data.get_last_closed_candle_df(
        symbol, config.ENTRY_TIMEFRAME_SWING, limit=250
    )
    if not binance_data.has_enough_data(entry_df):
        return None

    entry_df = indicators.add_all_indicators(entry_df)
    last = entry_df.iloc[-1]
    prev = entry_df.iloc[-2]

    support, resistance = indicators.find_support_resistance(entry_df, lookback=50)

    if trend_direction == "up":
        direction = "buy"
    elif trend_direction == "down":
        direction = "sell"
    else:
        return None

    # شرط الدخول: تقاطع MACD حديث في اتجاه الصفقة
    macd_cross_up = prev["macd"] <= prev["macd_signal"] and last["macd"] > last["macd_signal"]
    macd_cross_down = prev["macd"] >= prev["macd_signal"] and last["macd"] < last["macd_signal"]

    signal_valid = (direction == "buy" and macd_cross_up) or \
                   (direction == "sell" and macd_cross_down)

    entry_price = last["close"]
    buffer = config.STOP_LOSS_BUFFER_PERCENT / 100

    if direction == "buy":
        stop_loss = support * (1 - buffer)
        risk = entry_price - stop_loss
        target1 = entry_price + risk * config.MIN_RISK_REWARD_SWING
        target2 = entry_price + risk * (config.MIN_RISK_REWARD_SWING + 1)
    else:
        stop_loss = resistance * (1 + buffer)
        risk = stop_loss - entry_price
        target1 = entry_price - risk * config.MIN_RISK_REWARD_SWING
        target2 = entry_price - risk * (config.MIN_RISK_REWARD_SWING + 1)

    if risk <= 0:
        return None

    reward = abs(target1 - entry_price)
    risk_reward = reward / risk if risk > 0 else 0

    reason = (
        f"الاتجاه العام على فريم {config.TREND_TIMEFRAME} كان {trend_direction}. "
        f"على فريم {config.ENTRY_TIMEFRAME_SWING}: "
        f"{'تقاطع MACD إيجابي' if direction == 'buy' else 'تقاطع MACD سلبي'} حديث. "
        f"{indicators.explain_rsi(last['rsi'])}"
    )

    is_weak = not (signal_valid and risk_reward >= config.MIN_RISK_REWARD_SWING)

    return TradeSignal(
        symbol=symbol, trade_type="swing", direction=direction,
        entry=entry_price, stop_loss=stop_loss,
        target1=target1, target2=target2,
        risk_reward=risk_reward, reason=reason, is_weak=is_weak
    )


def scan_market(market_type: str = "spot"):
    """
    فحص أعلى العملات فوليوم، وإرجاع كل الفرص اللي لقاها (قوية أو ضعيفة)
    بيرجع list من TradeSignal مرتبة حسب الأولوية
    """
    symbols = binance_data.get_top_volume_symbols()
    results = []

    for symbol in symbols:
        signal, error = analyze_symbol(symbol, market_type)
        if signal:
            results.append(signal)

    results.sort(key=lambda s: (s.is_weak, -s.risk_reward))

    return results
