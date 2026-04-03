from vkbottle.bot import Message
from sqlalchemy import select

from config import settings
from db.database import async_session, managed_session
from db.models import User, Tunnel, VkSyncCode
from vk_bot.helpers import get_or_create_user, format_balance
from vk_bot.keyboards import main_menu_kb, back_kb


WELCOME = (
    "👻 Привет! Это GhostMode VPN.\n\n"
    "Быстрый VPN с защитой от блокировок РКН.\n"
    "Работает через ВКонтакте — даже при белых списках.\n\n"
    "⚡ Fast — ~$3/мес за устройство\n"
    "🧅 Ghost — ~$6/мес за устройство\n\n"
    "💡 Это VK-версия бота. Когда VPN заработает — переходи в "
    "@GhostModeVPN_bot: там удобнее и есть бонусы. "
    "Синхронизируй аккаунты через кнопку «🔗 Синхр. с Telegram».\n\n"
    "Выбери действие:"
)

WELCOME_NEW = (
    "👻 Привет! Это GhostMode VPN.\n\n"
    "Быстрый VPN с защитой от блокировок РКН.\n\n"
    "🎁 Мы зачислили тебе 1 день VPN бесплатно — "
    "этого хватит чтобы подключиться и зайти в Telegram.\n\n"
    "Как пользоваться:\n"
    "1. Нажми «📡 Мой VPN» → «➕ Добавить устройство»\n"
    "2. Выбери своё устройство и тариф\n"
    "3. Получи ключ и добавь в Hiddify\n\n"
    "Когда VPN заработает — открой @GhostModeVPN_bot в Telegram "
    "и синхронизируй аккаунт через кнопку «Синхр. с Telegram». "
    "Там удобнее и есть бонус $1 за подписку на канал.\n\n"
    "Выбери действие:"
)


async def cmd_start(message: Message):
    vk_id = message.from_id
    # Проверяем: есть ли код синхронизации в тексте
    text = (message.text or "").strip()
    if len(text) == 9 and text[4] == "-":
        # Выглядит как XXXX-XXXX — пробуем применить
        from bot.handlers.vk_sync import apply_sync_code, merge_accounts
        result = await apply_sync_code(text.upper(), vk_id=vk_id)
        if result == "ok":
            await message.answer(
                "✅ Аккаунты успешно синхронизированы!\n"
                "Теперь твои туннели и баланс доступны в обоих ботах.",
                keyboard=main_menu_kb()
            )
            return
        elif result == "already_linked":
            await message.answer(
                "ℹ️ Этот VK аккаунт уже привязан к Telegram.",
                keyboard=main_menu_kb()
            )
            return
        elif result and result.startswith("conflict:"):
            tg_user_id = int(result.split(":")[1])
            await message.answer(
                "⚠️ У тебя уже есть аккаунт в Telegram с данными.\n"
                "Объединить аккаунты? Баланс и туннели Telegram-аккаунта сохранятся.",
                keyboard=_merge_confirm_kb(tg_user_id, vk_id)
            )
            return

    user, is_new = await get_or_create_user(vk_id, "")
    if is_new:
        await message.answer(WELCOME_NEW, keyboard=main_menu_kb())
    else:
        await message.answer(WELCOME, keyboard=main_menu_kb())


def _merge_confirm_kb(tg_user_id: int, vk_id: int) -> str:
    from vkbottle import Keyboard, Text
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("✅ Объединить", payload={"cmd": "merge_confirm", "tg_uid": tg_user_id, "vk_id": vk_id}))
    kb.add(Text("❌ Отмена", payload={"cmd": "menu"}))
    return kb.get_json()


async def cmd_menu(message: Message):
    await get_or_create_user(message.from_id, "")
    await message.answer("Главное меню:", keyboard=main_menu_kb())


async def cmd_balance(message: Message):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id, "")
    async with managed_session() as db:
        result = await db.execute(
            select(Tunnel).where(Tunnel.user_id == user.id)
        )
        tunnels = result.scalars().all()
    text = format_balance(user, tunnels)
    await message.answer(text, keyboard=back_kb())


async def cmd_merge_confirm(message: Message, tg_user_id: int, vk_id: int):
    from bot.handlers.vk_sync import merge_accounts
    ok = await merge_accounts(tg_user_id=tg_user_id, vk_id=vk_id)
    if ok:
        await message.answer(
            "✅ Аккаунты объединены! Данные Telegram-аккаунта сохранены.",
            keyboard=main_menu_kb()
        )
    else:
        await message.answer("❌ Не удалось объединить.", keyboard=main_menu_kb())
