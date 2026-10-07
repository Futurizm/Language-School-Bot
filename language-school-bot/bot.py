import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from crm import create_lead

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── States ─────────────────────────────────────────────────────────────────
(
    MAIN_MENU,
    CHOOSE_LANGUAGE,
    CHOOSE_LEVEL,
    CHOOSE_FORMAT,
    GET_NAME,
    GET_PHONE,
    CONFIRM,
) = range(7)

# ─── School Data ─────────────────────────────────────────────────────────────
LANGUAGES = {
    "🇬🇧 Английский": "Английский",
    "🇩🇪 Немецкий": "Немецкий",
    "🇫🇷 Французский": "Французский",
    "🇪🇸 Испанский": "Испанский",
    "🇨🇳 Китайский": "Китайский",
    "🇰🇷 Корейский": "Корейский",
}

LEVELS = {
    "🟢 Начинающий (A1–A2)": "A1-A2",
    "🟡 Средний (B1–B2)": "B1-B2",
    "🔴 Продвинутый (C1–C2)": "C1-C2",
    "❓ Не знаю свой уровень": "Не определён",
}

FORMATS = {
    "👤 Индивидуально": "Индивидуально",
    "👥 Мини-группа (3–5 чел)": "Мини-группа",
    "🏫 Группа (6–12 чел)": "Группа",
    "💻 Онлайн": "Онлайн",
}

COURSES_INFO = """
📚 *Наши курсы*

*Английский* — от 15 000 ₸/мес
*Немецкий* — от 17 000 ₸/мес
*Французский* — от 17 000 ₸/мес
*Испанский* — от 16 000 ₸/мес
*Китайский* — от 18 000 ₸/мес
*Корейский* — от 18 000 ₸/мес

─────────────────────
📅 *Форматы обучения:*
• Индивидуальные занятия
• Мини-группы (3–5 человек)
• Группы (6–12 человек)
• Онлайн-формат

⏰ *Расписание:* Пн–Сб, 08:00–20:00
📍 *Адрес:* ул. Достык, 20, Алматы

Пробный урок — *БЕСПЛАТНО* 🎁
"""

CONTACTS_INFO = """
📞 *Контакты Lingo School*

📱 Телефон: +7 (777) 000-00-00
📬 WhatsApp: +7 (777) 000-00-01
📧 Email: info@lingo-school.kz
🌐 Сайт: lingo-school.kz

📍 Адрес: ул. Достык, 20, оф. 301
🏙 Алматы, Казахстан

🕐 Время работы:
Пн–Пт: 09:00–19:00
Сб: 10:00–16:00
"""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Записаться на пробный урок", callback_data="enroll")],
        [InlineKeyboardButton("📚 Курсы и цены", callback_data="courses")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton("❓ Часто задаваемые вопросы", callback_data="faq")],
    ])


def back_keyboard(back_to="main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
    ])


# ─── Handlers ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    name = update.effective_user.first_name or "друг"
    text = (
        f"👋 Привет, *{name}*\\!\n\n"
        "Добро пожаловать в *Lingo School* — языковую школу нового поколения\\.\n\n"
        "Мы поможем вам выучить язык быстро и с удовольствием\\. "
        "Что вас интересует?"
    )
    await update.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await query.edit_message_text(
            "🏠 *Главное меню*\n\nЧем могу помочь?",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if data == "courses":
        await query.edit_message_text(
            COURSES_INFO,
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )
        return MAIN_MENU

    if data == "contacts":
        await query.edit_message_text(
            CONTACTS_INFO,
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )
        return MAIN_MENU

    if data == "faq":
        faq_text = (
            "❓ *Часто задаваемые вопросы*\n\n"
            "*Как долго длится один курс?*\n"
            "Стандартный курс — 3 месяца (один уровень).\n\n"
            "*Сколько человек в группе?*\n"
            "Мини-группы: 3–5 чел., группы: 6–12 чел.\n\n"
            "*Можно ли перенести занятие?*\n"
            "Да, за 24 часа до занятия.\n\n"
            "*Есть ли пробный урок?*\n"
            "Да! Первый пробный урок — БЕСПЛАТНО 🎁\n\n"
            "*Как проходит онлайн-обучение?*\n"
            "Через Zoom или Google Meet, в удобное для вас время."
        )
        await query.edit_message_text(
            faq_text,
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )
        return MAIN_MENU

    if data == "enroll":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(lang, callback_data=f"lang_{lang}")]
            for lang in LANGUAGES.keys()
        ] + [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]])

        await query.edit_message_text(
            "🌍 *Шаг 1 из 4 — Выбор языка*\n\nКакой язык хотите изучать?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return CHOOSE_LANGUAGE

    return MAIN_MENU


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back_main":
        await query.edit_message_text(
            "🏠 *Главное меню*\n\nЧем могу помочь?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    lang_key = query.data.replace("lang_", "")
    context.user_data["language"] = LANGUAGES.get(lang_key, lang_key)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(lvl, callback_data=f"lvl_{lvl}")]
        for lvl in LEVELS.keys()
    ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back_lang")]])

    await query.edit_message_text(
        f"✅ Язык: *{context.user_data['language']}*\n\n"
        "📊 *Шаг 2 из 4 — Уровень*\n\nКакой у вас уровень?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return CHOOSE_LEVEL


async def choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back_lang":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(lang, callback_data=f"lang_{lang}")]
            for lang in LANGUAGES.keys()
        ] + [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]])
        await query.edit_message_text(
            "🌍 *Шаг 1 из 4 — Выбор языка*\n\nКакой язык хотите изучать?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return CHOOSE_LANGUAGE

    lvl_key = query.data.replace("lvl_", "")
    context.user_data["level"] = LEVELS.get(lvl_key, lvl_key)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(fmt, callback_data=f"fmt_{fmt}")]
        for fmt in FORMATS.keys()
    ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back_lvl")]])

    await query.edit_message_text(
        f"✅ Язык: *{context.user_data['language']}*\n"
        f"✅ Уровень: *{context.user_data['level']}*\n\n"
        "📋 *Шаг 3 из 4 — Формат*\n\nКакой формат обучения предпочитаете?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return CHOOSE_FORMAT


async def choose_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back_lvl":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(lvl, callback_data=f"lvl_{lvl}")]
            for lvl in LEVELS.keys()
        ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back_lang")]])
        await query.edit_message_text(
            f"✅ Язык: *{context.user_data['language']}*\n\n"
            "📊 *Шаг 2 из 4 — Уровень*\n\nКакой у вас уровень?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return CHOOSE_LEVEL

    fmt_key = query.data.replace("fmt_", "")
    context.user_data["format"] = FORMATS.get(fmt_key, fmt_key)

    await query.edit_message_text(
        f"✅ Язык: *{context.user_data['language']}*\n"
        f"✅ Уровень: *{context.user_data['level']}*\n"
        f"✅ Формат: *{context.user_data['format']}*\n\n"
        "👤 *Шаг 4 из 4 — Ваши данные*\n\n"
        "Как вас зовут? Напишите ваше *имя*:",
        parse_mode="Markdown"
    )
    return GET_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Пожалуйста, введите корректное имя (минимум 2 символа).")
        return GET_NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        f"Отлично, *{name}*! 👍\n\n"
        "Теперь введите ваш *номер телефона* (например: +7 777 000 00 00):",
        parse_mode="Markdown"
    )
    return GET_PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    # Basic validation
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await update.message.reply_text(
            "Пожалуйста, введите корректный номер телефона.\n"
            "Например: +7 777 000 00 00"
        )
        return GET_PHONE

    context.user_data["phone"] = phone
    ud = context.user_data

    summary = (
        "📋 *Подтверждение записи*\n\n"
        f"👤 Имя: *{ud['name']}*\n"
        f"📱 Телефон: *{ud['phone']}*\n"
        f"🌍 Язык: *{ud['language']}*\n"
        f"📊 Уровень: *{ud['level']}*\n"
        f"📋 Формат: *{ud['format']}*\n\n"
        "Всё верно? Наш менеджер свяжется с вами в течение 30 минут! 🎉"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_yes"),
            InlineKeyboardButton("✏️ Изменить", callback_data="confirm_no"),
        ]
    ])

    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=keyboard)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        context.user_data.clear()
        await query.edit_message_text(
            "Хорошо, начнём заново! 🔄",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    # ── Save to CRM ──────────────────────────────────────────────────────────
    ud = context.user_data
    tg_user = update.effective_user
    lead_data = {
        "name": ud["name"],
        "phone": ud["phone"],
        "language": ud["language"],
        "level": ud["level"],
        "format": ud["format"],
        "telegram_id": str(tg_user.id),
        "telegram_username": tg_user.username or "",
        "source": "Telegram Bot",
    }

    crm_ok, crm_message = create_lead(lead_data)

    if crm_ok:
        crm_note = "\n\n✅ Ваша заявка сохранена в нашей системе."
    else:
        # Экранируем возможные спецсимволы Markdown в сообщении об ошибке
        safe_msg = str(crm_message).replace("_", "\\_").replace("*", "\\*")
        crm_note = f"\n\n⚠️ Заявка принята, но CRM недоступна ({safe_msg})."
        logger.warning("CRM error: %s", crm_message)

    success_text = (
        "🎉 *Вы записаны на пробный урок!*\n\n"
        f"Имя: *{ud['name']}*\n"
        f"Телефон: *{ud['phone']}*\n"
        f"Язык: *{ud['language']}* ({ud['level']})\n"
        f"Формат: *{ud['format']}*"
        + crm_note +
        "\n\n📲 Наш менеджер позвонит вам в течение 30 минут.\n"
        "Спасибо, что выбрали *Lingo School*! 🏫"
    )

    await query.edit_message_text(
        success_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
        ])
    )

    context.user_data.clear()
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Диалог прерван. Напишите /start чтобы начать снова.",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "Переменная окружения TELEGRAM_BOT_TOKEN не задана!\n"
            "Создайте файл .env и добавьте: TELEGRAM_BOT_TOKEN=ваш_токен"
        )

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(main_menu_callback, pattern="^(enroll|courses|contacts|faq|back_main)$"),
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_callback, pattern="^(enroll|courses|contacts|faq|back_main)$"),
            ],
            CHOOSE_LANGUAGE: [
                CallbackQueryHandler(choose_language, pattern="^(lang_|back_main)"),
            ],
            CHOOSE_LEVEL: [
                CallbackQueryHandler(choose_level, pattern="^(lvl_|back_lang)"),
            ],
            CHOOSE_FORMAT: [
                CallbackQueryHandler(choose_format, pattern="^(fmt_|back_lvl)"),
            ],
            GET_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
            ],
            GET_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm, pattern="^confirm_"),
                CallbackQueryHandler(main_menu_callback, pattern="^back_main$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    logger.info("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    await app.initialize()
    await app.updater.start_polling(drop_pending_updates=True)
    await app.start()

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    main()
