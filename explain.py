"""
explain.py
منطق أمر /explain - بيشرح تفاصيل قرار الصفقة الأخيرة بشكل تعليمي
"""

import config


def build_explanation(signal) -> str:
    """
    بياخد TradeSignal (من analysis.py) ويحوله لشرح تعليمي مفصل بالعربي
    """
    if signal is None:
        return "مفيش صفقة أخيرة أشرحها. جرب /analyze أو /scan الأول."

    trade_type_ar = "سكالبينج (صفقة سريعة)" if signal.trade_type == "scalp" else "سوينج (صفقة تاخد وقت أطول)"
    direction_ar = "شراء" if signal.direction == "buy" else "بيع"

    weak_note = ""
    if signal.is_weak:
        weak_note = (
            "\n\n⚠️ ملاحظة مهمة: دي فرصة ضعيفة نسبيًا أو المخاطرة فيها أعلى من المعتاد، "
            "معروضة عليك لأنه مفيش فرصة أقوى متاحة دلوقتي. الحذر مطلوب أكتر من العادي."
        )

    explanation = f"""
📊 شرح تفصيلي لصفقة {signal.symbol}

**نوع الصفقة:** {trade_type_ar}
**الاتجاه:** {direction_ar}

**السبب الفني:**
{signal.reason}

**سعر الدخول:** {signal.entry:.6g}
**وقف الخسارة (Stop Loss):** {signal.stop_loss:.6g}
→ محسوب من أقرب مستوى دعم/مقاومة فعلي على الشارت، مش نسبة عشوائية.

**الهدف الأول:** {signal.target1:.6g}
**الهدف الثاني:** {signal.target2:.6g}

**نسبة المخاطرة للعائد (Risk/Reward):** 1:{signal.risk_reward:.2f}
→ يعني لو خسرت، هتخسر مبلغ X. ولو كسبت (الهدف الأول)، هتكسب X × {signal.risk_reward:.2f} تقريبًا.
{weak_note}

💡 تذكر: التحليل ده مبني على بيانات تاريخية (مؤشرات فنية)، مش تنبؤ مضمون. السوق ممكن يتحرك عكس التوقع في أي وقت.
"""
    return explanation.strip()
