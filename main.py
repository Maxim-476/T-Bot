import logging
import os
from enum import Enum

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class UserState(str, Enum):
    IDLE = "idle"
    FEEDBACK = "feedback"
    ORDER = "order"


BUTTON_FEEDBACK = "Обратная связь"
BUTTON_ORDER = "Сделать заказ"
BUTTON_HELP = "Помощь"


MENU_KEYBOARD = ReplyKeyboardMarkup(
    [[BUTTON_FEEDBACK, BUTTON_ORDER], [BUTTON_HELP]],
    resize_keyboard=True,
)


def get_order_hint() -> str:
    return (
        "Для оформления заказа отправьте одним сообщением:\n"
        "1. Номер телефона\n"
        "2. Товар\n"
        "3. Способ доставки: СДЭК, Почта или Яндекс\n"
        "4. Адрес доставки"
    )


async def send_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    user_name: str,
    user_id: int,
    text: str,
) -> bool:
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if not admin_chat_id:
        logger.warning("ADMIN_CHAT_ID is not set. Message was not forwarded.")
        return False

    message = (
        f"{title}\n"
        f"Пользователь: {user_name}\n"
        f"ID: {user_id}\n\n"
        f"{text}"
    )
    await context.bot.send_message(chat_id=admin_chat_id, text=message)
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["state"] = UserState.IDLE.value
    await update.message.reply_text(
        "Здравствуйте! Выберите действие на клавиатуре ниже.",
        reply_markup=MENU_KEYBOARD,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.text is None:
        return

    text = message.text.strip()
    state = context.user_data.get("state", UserState.IDLE.value)
    user = update.effective_user
    user_name = user.full_name if user else "Неизвестный пользователь"
    user_id = user.id if user else 0

    if text == BUTTON_FEEDBACK:
        context.user_data["state"] = UserState.FEEDBACK.value
        await message.reply_text(
            "Напишите ваше сообщение для обратной связи одним сообщением.",
            reply_markup=MENU_KEYBOARD,
        )
        return

    if text == BUTTON_ORDER:
        context.user_data["state"] = UserState.ORDER.value
        await message.reply_text(get_order_hint(), reply_markup=MENU_KEYBOARD)
        return

    if text == BUTTON_HELP:
        context.user_data["state"] = UserState.IDLE.value
        await message.reply_text(
            "Доступные разделы:\n"
            f"- {BUTTON_FEEDBACK}: отправить сообщение администратору.\n"
            f"- {BUTTON_ORDER}: оформить заказ.\n\n"
            f"{get_order_hint()}",
            reply_markup=MENU_KEYBOARD,
        )
        return

    if state == UserState.FEEDBACK.value:
        delivered = await send_to_admin(
            context,
            "Новая обратная связь",
            user_name,
            user_id,
            text,
        )
        context.user_data["state"] = UserState.IDLE.value
        if delivered:
            await message.reply_text(
                "Спасибо! Ваше сообщение отправлено администратору.",
                reply_markup=MENU_KEYBOARD,
            )
        else:
            await message.reply_text(
                "Сообщение получено, но `ADMIN_CHAT_ID` не настроен. "
                "Укажите его в переменных окружения, чтобы пересылать сообщения администратору.",
                reply_markup=MENU_KEYBOARD,
                parse_mode="Markdown",
            )
        return

    if state == UserState.ORDER.value:
        delivered = await send_to_admin(
            context,
            "Новый заказ",
            user_name,
            user_id,
            text,
        )
        context.user_data["state"] = UserState.IDLE.value
        if delivered:
            await message.reply_text(
                "Спасибо! Заказ отправлен администратору.",
                reply_markup=MENU_KEYBOARD,
            )
        else:
            await message.reply_text(
                "Заказ получен, но `ADMIN_CHAT_ID` не настроен. "
                "Укажите его в переменных окружения, чтобы пересылать заказы администратору.",
                reply_markup=MENU_KEYBOARD,
                parse_mode="Markdown",
            )
        return

    await message.reply_text(
        "Пожалуйста, выберите одну из кнопок меню.",
        reply_markup=MENU_KEYBOARD,
    )


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Environment variable BOT_TOKEN is required.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
