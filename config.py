# =========================================
# إعدادات البوت - كل الأرقام الثابتة هنا
# =========================================

# --- إعدادات عامة ---
MIN_CANDLES_REQUIRED = 210        # أقل عدد شمعات مطلوب عشان نثق في المؤشرات (عشان EMA200)
VOLATILITY_SPIKE_THRESHOLD = 8.0  # لو السعر اتحرك أكتر من 8% في آخر ساعة = تقلب مفاجئ

# --- فريمات التحليل ---
TREND_TIMEFRAME = "4h"      # الفريم اللي بيحدد الاتجاه العام (الحاكم)
ENTRY_TIMEFRAME_SCALP = "15m"   # فريم الدخول للسكالبينج
ENTRY_TIMEFRAME_SWING = "1d"    # فريم الدخول للسوينج

# --- إعدادات المؤشرات ---
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND_SHORT = 50
EMA_TREND_LONG = 200

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# --- إدارة المخاطرة ---
MIN_RISK_REWARD_SCALP = 1.5   # أقل نسبة مقبولة للسكالب (1:1.5)
MIN_RISK_REWARD_SWING = 2.0   # أقل نسبة مقبولة للسوينج (1:2)
STOP_LOSS_BUFFER_PERCENT = 0.3  # هامش أمان بسيط فوق/تحت الدعم والمقاومة

# --- عدد العملات في الفحص السريع ---
SCAN_TOP_N_COINS = 30   # هيفحص أعلى 30 عملة بالفوليوم في /scan
TOP_RESULTS_COUNT = 3   # عدد النتايج في /top3

# --- حماية من حظر Binance ---
REQUEST_DELAY_SECONDS = 0.3   # تأخير بسيط بين كل طلب وطلب في /scan
