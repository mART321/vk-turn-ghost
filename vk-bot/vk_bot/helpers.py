"""Вспомогательные функции для VK бота."""
import io
import qrcode
from sqlalchemy import select

from db.database import managed_session
from db.models import User
from config import settings


async def get_or_create_user(vk_id: int, first_name: str = "") -> tuple[User, bool]:
    """Получить или создать пользователя по vk_id. Возвращает (user, is_new)."""
    async with managed_session() as db:
        result = await db.execute(select(User).where(User.vk_id == vk_id))
        user = result.scalar_one_or_none()
        if not user:
            # Даём 1 бесплатный день Fast-тарифа чтобы пользователь мог зайти в Telegram
            user = User(
                vk_id=vk_id,
                username=str(vk_id),
                first_name=first_name,
                balance=round(settings.device_daily_rate, 4),
                ref_balance=0.0,
                notifications=True,
                trial_used=False,
                churn_survey_sent=False,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user, True
        return user, False


def days_word(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "дней"
    m = n % 10
    if m == 1:
        return "день"
    if 2 <= m <= 4:
        return "дня"
    return "дней"


def format_balance(user: User, tunnels: list) -> str:
    active = [t for t in tunnels if t.active]
    n = len(active)
    if n == 0:
        return (
            f"💰 Баланс: ${user.balance:.2f}\n\n"
            "⚡ Fast — ~$3/мес за устройство\n"
            "🧅 Ghost — ~$6/мес за устройство\n\n"
            "Нет активных туннелей — списания не идут."
        )
    daily = sum(
        settings.tor_daily_rate if (t.tier or "standard") == "tor" else settings.device_daily_rate
        for t in active
    )
    days = int(user.balance / daily) if daily > 0 else 0
    return (
        f"💰 Баланс: ${user.balance:.2f}\n"
        f"📡 Активных туннелей: {n}\n"
        f"💸 Списание: ${daily:.2f}/день\n"
        f"⏳ Хватит примерно на {days} {days_word(days)}"
    )


def make_qr_bytes(text: str) -> bytes:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
