"""
Синхронизация VK ↔ TG аккаунта.
VK бот генерирует код XXXX-XXXX, пользователь вводит его в TG боте.
"""
from datetime import datetime, timedelta
from vkbottle.bot import Message
from sqlalchemy import select, update

from db.database import async_session, managed_session
from db.models import VkSyncCode
from vk_bot.helpers import get_or_create_user
from vk_bot.keyboards import back_kb

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _gen_code() -> str:
    import secrets
    part = lambda: "".join(secrets.choice(ALPHABET) for _ in range(4))
    return f"{part()}-{part()}"


async def cmd_sync_tg(message: Message):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id, "")

    if user.telegram_id:
        await message.answer(
            f"✅ Аккаунт уже синхронизирован с Telegram.\n"
            f"TG ID: {user.telegram_id}",
            keyboard=back_kb()
        )
        return

    # Инвалидируем старые коды
    async with managed_session() as db:
        await db.execute(
            update(VkSyncCode)
            .where(VkSyncCode.vk_id == vk_id, VkSyncCode.used == False)
            .values(used=True)
        )
        code = _gen_code()
        sync = VkSyncCode(
            code=code,
            vk_id=vk_id,
            telegram_id=None,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            used=False,
        )
        db.add(sync)
        await db.commit()

    await message.answer(
        "🔗 Синхронизация с Telegram\n\n"
        f"Твой код:\n\n{code}\n\n"
        "Открой @GhostModeVPN_bot в Telegram и просто отправь этот код.\n"
        "Код действует 10 минут.",
        keyboard=back_kb()
    )
