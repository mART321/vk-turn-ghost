import urllib.parse
from vkbottle.bot import Message
from vkbottle import Keyboard, Text, OpenLink
from sqlalchemy import select, func

from config import settings
from db.database import async_session, managed_session
from db.models import User, Referral
from vk_bot.helpers import get_or_create_user


async def cmd_referral(message: Message):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)

    async with managed_session() as db:
        invited_result = await db.execute(
            select(func.count()).where(User.referrer_id == user.id)
        )
        invited_count = invited_result.scalar() or 0

        earned_result = await db.execute(
            select(func.sum(Referral.bonus_usdt)).where(Referral.referrer_id == user.id)
        )
        earned = earned_result.scalar() or 0.0

    ref_link = f"https://vk.com/ghostmodevpn?ref={user.id}"
    share_url = (
        "https://vk.com/share.php?"
        f"url={urllib.parse.quote(ref_link)}&"
        f"title={urllib.parse.quote('GhostMode VPN — быстрый VPN без блокировок 👻')}"
    )

    text = (
        "👥 Реферальная программа\n\n"
        f"Приглашай друзей и получай ${settings.referral_bonus:.2f} (~10 дней VPN) "
        "за каждого оплатившего!\n\n"
        f"Твоя ссылка:\n{ref_link}\n\n"
        "Статистика:\n"
        f"• Приглашено: {invited_count} чел.\n"
        f"• Заработано: ${earned:.2f}"
    )

    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(share_url, "📤 Поделиться с другом"))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))

    await message.answer(text, keyboard=kb.get_json())
