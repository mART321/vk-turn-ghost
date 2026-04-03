import hashlib
from datetime import datetime
from vkbottle.bot import Message
from sqlalchemy import select

from config import settings
from db.database import async_session, managed_session
from db.models import User, Payment
from services.payment_service import get_usdt_rub_rate, create_yukassa_payment
from vk_bot.helpers import get_or_create_user, make_qr_bytes
from vk_bot.keyboards import (
    back_kb, topup_kb, main_menu_kb, sbp_amount_kb, sbp_invoice_kb,
)

AMOUNTS = [3, 6, 12]


async def cmd_topup(message: Message):
    rate = await get_usdt_rub_rate()
    if rate:
        fast_rub = round(0.09 * 30 * rate)
        ghost_rub = round(0.19 * 30 * rate)
        tariffs = (
            f"⚡ Fast — ~$3/мес (~{fast_rub}₽/мес)\n"
            f"🧅 Ghost — ~$6/мес (~{ghost_rub}₽/мес)"
        )
    else:
        tariffs = "⚡ Fast — ~$3/мес\n🧅 Ghost — ~$6/мес"

    await message.answer(
        f"💳 Пополнить баланс\n\n{tariffs}\n\nВыбери способ оплаты:",
        keyboard=topup_kb()
    )


# ─── СБП ──────────────────────────────────────────────────────────────────────

async def cmd_topup_sbp(message: Message):
    rate = await get_usdt_rub_rate()
    lines = []
    for a in AMOUNTS:
        rub = f" ≈ {round(a * rate)}₽" if rate else ""
        lines.append(f"${a}{rub}")
    await message.answer(
        "📱 Оплата по QR-коду (СБП)\n\n"
        "Сканируете QR — подтверждаете в приложении банка.\n\n"
        "Выберите сумму:\n" + " | ".join(lines),
        keyboard=sbp_amount_kb()
    )


async def cmd_topup_sbp_amount(message: Message, amount: int):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    amount_usd = float(amount)

    rate = await get_usdt_rub_rate()
    amount_rub = round(amount_usd * rate) if rate else round(amount_usd * 90)

    invoice = await create_yukassa_payment(amount_usd, amount_rub, method="sbp")
    if not invoice:
        await message.answer("❌ Ошибка создания платежа. Попробуйте позже.", keyboard=back_kb())
        return

    async with managed_session() as db:
        payment = Payment(
            user_id=user.id,
            amount_usdt=amount_usd,
            currency="YUKASSA",
            invoice_id=invoice["payment_id"],
            status="pending",
        )
        db.add(payment)
        await db.commit()

    await message.answer(
        f"📱 Оплата по QR-коду (СБП)\n\n"
        f"Сумма: {amount_rub} ₽ (${amount_usd:.2f})\n\n"
        "Откройте QR-код и отсканируйте в приложении банка.\n"
        "Баланс зачислится автоматически в течение минуты после оплаты.",
        keyboard=sbp_invoice_kb(invoice["confirmation_url"])
    )


# ─── USDT (TON) ───────────────────────────────────────────────────────────────

def _usdt_amount_kb():
    from vkbottle import Keyboard, Text
    kb = Keyboard(one_time=False, inline=False)
    for a in AMOUNTS:
        kb.add(Text(f"${a}", payload={"cmd": "topup_usdt_amount", "amount": a}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "topup"}))
    return kb.get_json()


def _ton_amount_kb():
    from vkbottle import Keyboard, Text
    kb = Keyboard(one_time=False, inline=False)
    for a in AMOUNTS:
        kb.add(Text(f"${a}", payload={"cmd": "topup_ton_amount", "amount": a}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "topup"}))
    return kb.get_json()


async def cmd_topup_usdt(message: Message):
    await message.answer(
        "💵 Выбери сумму пополнения (USDT на TON):",
        keyboard=_usdt_amount_kb()
    )


async def cmd_topup_ton(message: Message):
    await message.answer(
        "💎 Выбери сумму пополнения (TON):",
        keyboard=_ton_amount_kb()
    )


async def _create_crypto_invoice(message: Message, currency: str, amount_usd: float, api, upload):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)

    memo = hashlib.md5(
        f"{user.id}:{currency}:{amount_usd}:{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:8].upper()

    async with managed_session() as db:
        payment = Payment(
            user_id=user.id,
            currency=currency,
            amount_usdt=amount_usd,
            invoice_id=memo,
            status="pending",
        )
        db.add(payment)
        await db.commit()

    wallet = settings.ton_wallet
    if currency == "USDT":
        text = (
            f"💵 Оплата {amount_usd}$ в USDT (TON)\n\n"
            f"Кошелёк: {wallet}\n"
            f"Сеть: TON\n"
            f"Сумма: {amount_usd} USDT\n"
            f"Комментарий (memo): {memo}\n\n"
            "⚠️ Обязательно укажи комментарий!\n"
            "Баланс зачислится автоматически в течение минуты."
        )
        qr_text = f"ton://transfer/{wallet}?amount={int(amount_usd * 1e6)}&text={memo}"
    else:
        ton_amount = round(amount_usd / 3.0, 2)
        text = (
            f"💎 Оплата {amount_usd}$ в TON\n\n"
            f"Кошелёк: {wallet}\n"
            f"Сеть: TON\n"
            f"Сумма: ~{ton_amount} TON\n"
            f"Комментарий (memo): {memo}\n\n"
            "⚠️ Обязательно укажи комментарий!\n"
            "Баланс зачислится автоматически в течение минуты."
        )
        qr_text = f"ton://transfer/{wallet}?amount={int(ton_amount * 1e9)}&text={memo}"

    await message.answer(text, keyboard=back_kb())

    try:
        qr_bytes = make_qr_bytes(qr_text)
        photo = await upload.photo_messages(qr_bytes, peer_id=message.peer_id)
        await api.messages.send(
            peer_id=message.peer_id,
            attachment=f"photo{photo[0].owner_id}_{photo[0].id}",
            random_id=0,
        )
    except Exception:
        pass


async def cmd_topup_usdt_amount(message: Message, amount: int, api, upload):
    await _create_crypto_invoice(message, "USDT", float(amount), api, upload)


async def cmd_topup_ton_amount(message: Message, amount: int, api, upload):
    await _create_crypto_invoice(message, "TON", float(amount), api, upload)
