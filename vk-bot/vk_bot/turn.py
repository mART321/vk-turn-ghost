"""
VK TURN — обход белых списков. Уникальная функция VK бота.
"""
import re
from vkbottle.bot import Message
from sqlalchemy import select

from db.database import managed_session
from db.models import User, Tunnel
from services.turn_service import VK_OAUTH_URL, extract_token, create_vk_call, save_turn_link, get_expiring_turn_users
from config import settings
from services.turn_service import encrypt_link
from vk_bot.helpers import get_or_create_user
from vk_bot.keyboards import turn_kb, turn_success_kb, back_kb, main_menu_kb, turn_menu_kb

_INSTRUCTION = (
    "🔑 Обход белых списков\n\n"
    "Этот режим маршрутизирует VPN через серверы ВКонтакте — "
    "они всегда в белом списке РКН.\n\n"
    "Как подключиться:\n"
    "1. Скачай приложение GhostMode — инструкция в разделе «📖 Как пользоваться»\n"
    "2. Добавь подписку по ссылке из «📡 Мой VPN → Ключ»\n"
    "3. В приложении появится конфиг «VK TURN» — выбери его\n"
    "4. VPN автоматически подключится через серверы ВКонтакте\n\n"
    "Никакой дополнительной авторизации не нужно."
)

_NO_SUBSCRIPTION = (
    "❌ У тебя нет активной подписки.\n\n"
    "Обход белых списков доступен только при наличии VPN-туннеля. "
    "Создай туннель в разделе «📡 Мой VPN»."
)

# Регулярка для перехвата URL или голого токена (оставляем для обратной совместимости)
TOKEN_RE = re.compile(r"oauth\.vk\.com/blank\.html#access_token=|^vk1\.a\.")

# Регулярка для детекта "не той" ссылки
_WRONG_URL_RE = re.compile(r"oauth\.vk\.com/authorize")


async def _has_active_tunnel(vk_id: int) -> bool:
    """Возвращает True если у пользователя есть хотя бы один активный туннель."""
    async with managed_session() as db:
        result = await db.execute(select(User).where(User.vk_id == vk_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        result2 = await db.execute(
            select(Tunnel).where(Tunnel.user_id == user.id, Tunnel.active == True)
        )
        return result2.scalar_one_or_none() is not None


async def cmd_turn(message: Message):
    if not await _has_active_tunnel(message.from_id):
        await message.answer(_NO_SUBSCRIPTION, keyboard=back_kb())
        return
    await message.answer(_INSTRUCTION, keyboard=turn_menu_kb())


async def cmd_turn_get_link(message: Message):
    """Отправляет зашифрованную ссылку пользователю для вставки в приложение."""
    if not await _has_active_tunnel(message.from_id):
        await message.answer(_NO_SUBSCRIPTION, keyboard=back_kb())
        return

    if not settings.vk_turn_link:
        await message.answer(
            "⚠️ Ссылка временно недоступна. Попробуй позже.",
            keyboard=turn_menu_kb(),
        )
        return

    encrypted = encrypt_link(settings.vk_turn_link)
    await message.answer(
        "📋 Зашифрованная ссылка для приложения GhostMode:\n\n"
        f"`{encrypted}`\n\n"
        "Как использовать:\n"
        "1. Скопируй строку выше\n"
        "2. Открой GhostMode → Настройки → VK TURN\n"
        "3. Вставь в поле «Вставить ссылку вручную» → нажми Применить\n"
        "4. Нажми «Подключить» — VPN заработает через серверы ВКонтакте",
        keyboard=turn_menu_kb(),
    )


async def handle_oauth_url(message: Message):
    """Перехватывает вставленный OAuth URL или голый токен."""
    text = message.text or ""

    # Пользователь прислал авторизационную ссылку вместо callback
    if _WRONG_URL_RE.search(text):
        await message.answer(
            "⚠️ Это ссылка для входа, а не результат авторизации.\n\n"
            "Нужно:\n"
            "1. Открыть ссылку из кнопки «Открыть страницу VK»\n"
            "2. Нажать «Разрешить» на странице VK\n"
            "3. Браузер перейдёт на пустую страницу — скопируй адрес из адресной строки и пришли сюда\n\n"
            "Адрес должен начинаться с: https://oauth.vk.com/blank.html#access_token=...",
            keyboard=turn_kb(VK_OAUTH_URL)
        )
        return True

    token = extract_token(text)
    if not token:
        return False  # не наш формат

    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id, "")

    await message.answer("⏳ Получаю ключ...")

    join_link = await create_vk_call(token)
    if not join_link:
        await message.answer(
            "❌ Не удалось получить ключ. Возможно токен недействителен.\n"
            "Попробуй заново — нажми «🔑 Обход блокировок».",
            keyboard=main_menu_kb()
        )
        return True

    await save_turn_link(user.id, token, join_link)

    await message.answer(
        "✅ Ключ обхода активирован!\n\n"
        "Твой VPN теперь работает даже при белых списках РКН.\n"
        "Ключ действует 24 часа — когда истечёт, пришлём напоминание.",
        keyboard=turn_success_kb()
    )
    return True


async def notify_expired_turn_tokens(bot):
    """Уведомить пользователей у которых истёк TURN токен. Вызывается из scheduler."""
    users = await get_expiring_turn_users()
    for user in users:
        if not user.vk_id:
            continue
        # Сбросить ссылку
        async with managed_session() as db:
            u = await db.get(User, user.id)
            if u:
                u.turn_join_link = None
                u.vk_token = None
                u.turn_link_expires_at = None
                await db.commit()
        try:
            from vkbottle import Keyboard, Text
            kb = Keyboard(one_time=False, inline=False)
            kb.add(Text("🔑 Обновить ключ", payload={"cmd": "turn"}))
            await bot.api.messages.send(
                user_id=user.vk_id,
                message=(
                    "🔑 Ключ обхода белых списков истёк.\n\n"
                    "Когда понадобится — обнови его кнопкой ниже."
                ),
                keyboard=kb.get_json(),
                random_id=0,
            )
        except Exception:
            pass
