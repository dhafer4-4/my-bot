import pandas as pd
import os
import qrcode
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# --- الإعدادات النهائية لبوت 2026 ---
TOKEN = "8364285434:AAHk8kHIROCVfaslWbGnju1Gf2zYiY6I1uI"
FONT_PATH = "arial.ttf"

# خريطة الأشهر - تأكد من رفع ملفات الإكسل بنفس الأسماء (Mar.xlsx, Feb.xlsx, Jan.xlsx)
MONTHS_FILES = {
    "كانون الثاني": "Jan.xlsx",
    "شباط": "Feb.xlsx",
    "آذار": "Mar.xlsx"
}

def fix_ar(text):
    if pd.isna(text) or str(text).strip() in ["nan", "None", "", "0", "0.0"]: return ""
    val = str(text)
    if val.endswith('.0'): val = val[:-2]
    return get_display(reshape(val))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في نظام الأتمتة الإدارية (نسخة Koyeb الاحترافية) 🏢\nالمحاسب المسؤول: ظافر عزيز\n\nأدخل اسم الموظف للبحث في الأرشيف:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    try:
        # نبحث بملف آذار كفحص أولي للاسم
        df = pd.read_excel("Mar.xlsx")
        results = df[df.iloc[:, 0].astype(str).str.contains(query, na=False)]
    except Exception as e:
        await update.message.reply_text("عذراً حجي، تأكد من رفع ملفات الإكسل (مثل Mar.xlsx) للمخزن.")
        return

    if results.empty:
        await update.message.reply_text("الاسم غير موجود في سجلاتنا.")
    elif len(results) > 5:
        await update.message.reply_text("النتائج كثيرة، يرجى كتابة الاسم الثلاثي بدقة.")
    else:
        for idx, row in results.iterrows():
            name_val = str(row.iloc[0])
            keyboard = [[InlineKeyboardButton(f"📅 تقرير شهر {m}", callback_data=f"sel_{m}_{name_val}")] for m in MONTHS_FILES.keys()]
            await update.message.reply_text(f"👤 الموظف: {name_val}\nاختر الشهر المطلوب سحب تقريره:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    , m_name, emp_name = query.data.split('')
    
    keyboard = [
        [InlineKeyboardButton("📄 سجل المعلومات العامة", callback_data=f"doc_W_{m_name}_{emp_name}")],
        [InlineKeyboardButton("💰 كشف المستحقات المالية", callback_data=f"doc_Q_{m_name}_{emp_name}")]
    ]
    await query.edit_message_text(text=f"الموظف: {emp_name}\nالشهر المختار: {m_name}\nاختر نوع التقرير المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))

async def generate_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    , sheet, m_name, emp_name = query.data.split('')
    
    file_path = MONTHS_FILES.get(m_name)
    try:
        df = pd.read_excel(file_path, sheet_name=sheet)
        row = df[df.iloc[:, 0].astype(str) == emp_name].iloc[0]
    except:
        await query.message.reply_text(f"خطأ: ملف شهر {m_name} غير موجود حالياً.")
        return

    # إنشاء ملف الـ PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("ArialAR", "", FONT_PATH)
    
    # تصميم رأس التقرير (Header)
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(10, 10, 190, 25, 'F')
    pdf.set_font("ArialAR", size=16)
    pdf.cell(190, 15, text=fix_ar(f"تقرير {m_name} الرسمي - قسم شرق بغداد"), align='C', ln=1)
    pdf.set_font("ArialAR", size=10)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(190, 10, text=fix_ar(f"تاريخ الإصدار: {now}"), align='C', ln=1)
    pdf.ln(10)

    # تفاصيل البيانات
    pdf.set_font("ArialAR", size=11)
    for col, val in row.to_dict().items():
        val_str = str(val).strip()
        if val_str.lower() not in ["nan", "none", "", "0", "0.0"]:
            pdf.cell(130, 9, text=fix_ar(val_str), border='B', align='R')
            pdf.cell(60, 9, text=fix_ar(col + " :"), border='B', align='R')
            pdf.ln(9)

    # إنشاء الباركود (QR Code) للتأكد من صحة التقرير
    qr_text = f"Verified: {emp_name}\nMonth: {m_name}\nAuth: Dhafer Aziz System"
    qrcode.make(qr_text).save("temp_qr.png")
    pdf.image("temp_qr.png", x=10, y=pdf.get_y()+10, w=30)
    
    # تذييل الصفحة
    pdf.set_y(270)
    pdf.set_font("ArialAR", size=8)
    pdf.cell(190, 10, text=fix_ar("نظام الأتمتة الإدارية - المحاسب ظافر عزيز 2026"), align='C')

    file_name = f"{emp_name}_{m_name}.pdf"
    pdf.output(file_name)
    with open(file_name, 'rb') as f:
        await context.bot.send_document(chat_id=query.message.chat_id, document=f, caption=f"تم إصدار تقرير شهر {m_name} بنجاح ✅")
    
    # تنظيف الملفات المؤقتة من السيرفر
    os.remove(file_name)
    os.remove("temp_qr.png")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button, pattern="^sel_"))
    app.add_handler(CallbackQueryHandler(generate_doc, pattern="^doc_"))
    print("🚀 البوت انطلق بنجاح على سيرفر Koyeb..")
    app.run_polling()