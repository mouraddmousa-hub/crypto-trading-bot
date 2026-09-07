"""
main.py
الملف الرئيسي - بيدير أوامر تليجرام وبيربط كل حاجة ببعض
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

import analysis
import explain as explain_module
import binance_data

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# تخزين مؤقت في الذاكرة - آخر صفقة اتحللت لكل مستخدم (عشان /explain)
last_signal_per_user = {}
# تخزين مؤقت - آخر نتايج /scan لكل مستخدم (عشان /top3)
last_scan_per_user = {}
# تخزين مؤقت - العملة اللي المستخدم طلب تحليلها وبستنى يختار سبوت/فيوتشرز
pending_analysis = {}


# ============ أوامر البوت ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "أهلاً بيك 👋\n\n"
        "الأوامر المتاحة:\n"
        "/analyze [عملة] - تحليل عملة معينة (مثال: /analyze BTC)\n"
        "/scan - فحص السوق بالكامل عن فرص\n"
        "/top3 - أفضل 3 فرص من آخر فحص\n"
        "/explain - شرح تفصيلي لآخر صفقة اتحللت\n\n"
        "⚠️ تذكير: البوت بيدي تحليل فني بس، مش نصيحة مالية أو ضمان ربح."
    )
    await update.message.reply_text(text)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("اكتب اسم العملة كده: /analyze BTC")
        return

    symbol_input = context.args[0].upper()
    pending_analysis[user_id] = symbol_input

    keyboard = [
        [
            InlineKeyboardButton("سبوت", callback_data="analyze_spot"),
            InlineKeyboardButton("فيوتشرز", callback_data="analyze_futures"),
        ]
    ]
    await update.message.reply_text(
        f"هتحلل {symbol_input} كـ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("سبوت", callback_data="scan_spot"),
            InlineKeyboardButton("فيوتشرز", callback_data="scan_futures"),
        ]
    ]
    await update.message.reply_text(
        "هتفحص السوق كـ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def top3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    results = last_scan_per_user.get(user_id)

    if not results:
        await update.message.reply_text("لازم تعمل /scan الأول قبل ما تطلب /top3")
        return

    top3 = results[:3]
    await update.message.reply_text(_format_scan_summary(top3, title="🏆 أفضل 3 فرص"))


async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    signal = last_signal_per_user.get(user_id)
    text = explain_module.build_explanation(signal)
    await update.message.reply_text(text, parse_mode="Markdown")


# ============ التعامل مع ضغط الأزرار ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data in ("analyze_spot", "analyze_futures"):
        market_type = "spot" if query.data == "analyze_spot" else "futures"
        symbol_input = pending_analysis.get(user_id)

        if not symbol_input:
            await query.edit_message_text("حصل خطأ، جرب /analyze تاني")
            return

        await query.edit_message_text(f"⏳ بحلل {symbol_input} ({market_type})...")

        full_symbol = symbol_input if symbol_input.endswith("USDT") else symbol_input + "USDT"
        signal, error = analysis.analyze_symbol(full_symbol, market_type)

        if error and not signal:
            await query.edit_message_text(f"❌ {error}")
            return

        last_signal_per_user[user_id] = signal
        text = _format_signal(signal)
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data in ("scan_spot", "scan_futures"):
        market_type = "spot" if query.data == "scan_spot" else "futures"
        await query.edit_message_text(f"⏳ بفحص السوق ({market_type})... ده ممكن ياخد دقيقة أو اتنين")

        results = analysis.scan_market(market_type)
        last_scan_per_user[user_id] = results

        if not results:
            await query.edit_message_text("مفيش أي فرص متاحة دلوقتي في السوق كله")
            return

        if results:
            last_signal_per_user[user_id] = results[0]

        text = _format_scan_summary(results, title=f"📈 نتائج الفحص ({len(results)} فرصة)")
        await query.edit_message_text(text, parse_mode="Markdown")


# ============ دوال تنسيق الرسائل ============

def _format_signal(signal) -> str:
    if signal is None:
        return "مفيش صفقة متاحة"

    trade_type_ar = "سكالبينج ⚡" if signal.trade_type == "scalp" else "سوينج 📅"
    direction_ar = "شراء 🟢" if signal.direction == "buy" else "بيع 🔴"
    weak_flag = "\n⚠️ فرصة ضعيفة نسبيًا / مخاطرة أعلى من المعتاد" if signal.is_weak else ""

    return f"""
**{signal.symbol}** - {trade_type_ar}
الاتجاه: {direction_ar}

الدخول: `{signal.entry:.6g}`
وقف الخسارة: `{signal.stop_loss:.6g}`
الهدف الأول: `{signal.target1:.6g}`
الهدف الثاني: `{signal.target2:.6g}`
Risk/Reward: 1:{signal.risk_reward:.2f}
{weak_flag}

اكتب /explain لشرح تفصيلي لسبب الصفقة دي
""".strip()


def _format_scan_summary(results, title="النتائج") -> str:
    lines = [f"**{title}**\n"]
    for i, s in enumerate(results, 1):
        trade_type_ar = "سكالب" if s.trade_type == "scalp" else "سوينج"
        direction_ar = "شراء" if s.direction == "buy" else "بيع"
        weak_mark = " ⚠️" if s.is_weak else " ✅"
        lines.append(
            f"{i}. **{s.symbol}** - {trade_type_ar} - {direction_ar}{weak_mark}\n"
            f"   دخول: `{s.entry:.6g}` | R/R: 1:{s.risk_reward:.2f}"
        )
    lines.append("\nاستخدم /analyze [عملة] لتفاصيل أي واحدة منهم")
    return "\n".join(lines)


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مش فاهم الأمر ده. جرب /start عشان تشوف الأوامر المتاحة."
    )


# ============ تشغيل البوت ============

def main():
    if not BOT_TOKEN:
        raise ValueError("لازم تحط TELEGRAM_BOT_TOKEN في environment variables")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("top3", top3_command))
    app.add_handler(CommandHandler("explain", explain_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    logger.info("البوت شغال...")
    app.run_polling()


if __name__ == "__main__":
    main()
