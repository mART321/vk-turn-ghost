import json
from datetime import datetime, timedelta, date
from vkbottle.bot import Message
from sqlalchemy import select, func

from db.database import async_session, managed_session
from db.models import User, Tunnel, DailyCharge
from services.node_manager import node_manager
try:
    from services.scheduler import get_scheduler, charge_after_grace
except ImportError:
    def get_scheduler():
        return None
    async def charge_after_grace(*args, **kwargs):
        pass
from config import settings
from vk_bot.helpers import get_or_create_user, make_qr_bytes
from vk_bot.keyboards import (
    main_menu_kb, back_kb, tunnel_list_kb, tunnel_detail_kb,
    delete_confirm_kb, tier_switch_confirm_kb, device_type_kb, tariff_kb,
)

SUB_HOST = "https://ghost-mode.ru:8443/sub"

LABEL_MAP = {
    "iPhone":  "📱 iPhone",
    "Android": "🤖 Android",
    "Mac":     "💻 Mac",
    "Windows": "🖥 Windows",
    "TV":      "📺 Smart TV",
}


def _tier_label(tier: str) -> str:
    return "🧅 Ghost — VPN + Tor" if tier == "tor" else "⚡ Fast — VPN"


def _configs_text(tier: str) -> str:
    if tier == "tor":
        return "5 конфигов: Fast, Russia, H2, XHTTP, Tor"
    return "3 конфига: Fast, Russia, H2"


def _sub_url(key_id: str) -> str:
    return f"{SUB_HOST}/{key_id}"


def _tunnel_daily_cost(tunnels: list) -> float:
    return round(sum(
        settings.tor_daily_rate if getattr(t, "tier", "standard") == "tor"
        else settings.device_daily_rate
        for t in tunnels
    ), 4)


async def _send_qr(message: Message, qr_text: str, api, upload):
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


async def cmd_tunnels(message: Message):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        result = await db.execute(
            select(Tunnel).where(Tunnel.user_id == user.id).order_by(Tunnel.slot)
        )
        tunnels = result.scalars().all()

    if not tunnels:
        await message.answer(
            "📡 Мой VPN\n\n"
            "У тебя нет устройств.\n\n"
            "⚡ Fast — ~$3/мес за устройство\n"
            "🧅 Ghost — ~$6/мес за устройство\n\n"
            "Добавь первое устройство:",
            keyboard=tunnel_list_kb([])
        )
        return

    active = [t for t in tunnels if t.active]
    daily = _tunnel_daily_cost(active)
    days = round(user.balance / daily) if daily > 0 else 0
    await message.answer(
        f"📡 Мой VPN\n\n"
        f"Активных устройств: {len(active)}\n"
        f"Списывается: ${daily}/день\n"
        f"Осталось: ~{days} дн.\n\n"
        "Выбери устройство:",
        keyboard=tunnel_list_kb(tunnels)
    )


async def cmd_tunnel_info(message: Message, tunnel_id: int):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)

    if not t or t.user_id != user.id:
        await message.answer("Туннель не найден.", keyboard=main_menu_kb())
        return

    tier = t.tier or "standard"
    rate = settings.tor_daily_rate if tier == "tor" else settings.device_daily_rate
    status = "🟢 Активен" if t.active else "🔴 Отключён"
    location = node_manager.get_node_location(t.node_id) if t.node_id else "—"

    await message.answer(
        f"{t.label or 'Устройство'}\n\n"
        f"Статус: {status}\n"
        f"Нода: {location}\n"
        f"Тариф: {_tier_label(tier)} (${rate}/день)",
        keyboard=tunnel_detail_kb(t.id, tier)
    )


async def cmd_create_tunnel(message: Message):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    if user.balance < settings.device_daily_rate:
        await message.answer(
            f"❌ Недостаточно баланса.\n"
            f"Нужно минимум ${settings.device_daily_rate} (1 день).\n\n"
            "Пополни счёт:",
            keyboard=main_menu_kb()
        )
        return
    await message.answer(
        "📱 Выбери тип устройства:\n\nЭто поможет отличать туннели друг от друга.",
        keyboard=device_type_kb()
    )


async def cmd_tunnel_device(message: Message, device: str):
    label = LABEL_MAP.get(device, device)
    await message.answer(
        f"📡 Выбери тариф для {label}\n\n"
        "⚡ Fast — VPN\n"
        "3 конфига: Fast, Russia, H2.\n"
        "Подходит для большинства задач.\n"
        "Цена: ~$3/мес\n\n"
        "🧅 Ghost — VPN + Tor\n"
        "5 конфигов: Fast, Russia, H2, XHTTP и Tor.\n"
        "Максимальная анонимность, IP не отслеживается.\n"
        "Цена: ~$6/мес",
        keyboard=tariff_kb(device)
    )


async def cmd_tunnel_tier(message: Message, device: str, tier: str, api, upload):
    vk_id = message.from_id
    label = LABEL_MAP.get(device, device)
    rate = settings.tor_daily_rate if tier == "tor" else settings.device_daily_rate

    async with managed_session() as db:
        result = await db.execute(select(User).where(User.vk_id == vk_id))
        user = result.scalar_one_or_none()

    if not user or user.balance < rate:
        await message.answer(
            f"❌ Недостаточно баланса. Нужно минимум ${rate:.2f} (1 день).",
            keyboard=main_menu_kb()
        )
        return

    await message.answer(f"⏳ Создаю туннель для {label}...")

    # Читаем данные и закрываем сессию ДО обращения к Marzban API
    async with managed_session() as db:
        result = await db.execute(select(User).where(User.vk_id == vk_id))
        user = result.scalar_one_or_none()

        max_slot_result = await db.execute(
            select(func.max(Tunnel.slot)).where(Tunnel.user_id == user.id)
        )
        max_slot = max_slot_result.scalar() or 0

        same_count_result = await db.execute(
            select(func.count()).where(
                Tunnel.user_id == user.id,
                Tunnel.label.like(f"{label}%")
            )
        )
        same_count = same_count_result.scalar() or 0
        final_label = f"{label} №{same_count + 1}" if same_count > 0 else label
        user_id = user.id

    # Создаём ключ в Marzban — без открытой DB сессии (может занять несколько секунд)
    try:
        key_data = await node_manager.create_key(tier=tier)
    except Exception as e:
        await message.answer(
            f"❌ Ошибка создания туннеля: {e}\n\nОбратитесь в поддержку.",
            keyboard=main_menu_kb()
        )
        return

    # Сохраняем в БД свежей сессией
    try:
        async with managed_session() as db:
            tunnel = Tunnel(
                user_id=user_id,
                slot=max_slot + 1,
                label=final_label,
                key_id=key_data["key_id"],
                key_id_2=key_data.get("key_id_2"),
                key_id_3=key_data.get("key_id_3"),
                key_id_4=key_data.get("key_id_4"),
                node_id=key_data["node_id"],
                key_string=key_data["key_string"],
                sub_links=json.dumps(key_data["sub_links"]) if key_data.get("sub_links") else None,
                tier=tier,
                wg_private_key=key_data.get("wg_private_key"),
                wg_address=key_data.get("wg_address"),
                active=True,
            )
            db.add(tunnel)
            await db.commit()
            await db.refresh(tunnel)

        scheduler = get_scheduler()
        if scheduler:
            scheduler.add_job(
                charge_after_grace,
                "date",
                run_date=datetime.utcnow() + timedelta(minutes=5),
                args=[tunnel.id, user_id],
            )
    except Exception as e:
        # Ключ создан в Marzban, но не сохранён — удаляем чтобы не висел мусор
        try:
            await node_manager.delete_key(
                key_data["node_id"], key_data["key_id"],
                key_data.get("key_id_2"), key_data.get("key_id_3"), key_data.get("key_id_4")
            )
        except Exception:
            pass
        await message.answer(
            f"❌ Ошибка сохранения туннеля: {e}\n\nОбратитесь в поддержку.",
            keyboard=main_menu_kb()
        )
        return

    sub_url = _sub_url(key_data["key_id"])
    await message.answer(
        f"✅ {final_label} — туннель создан!\n"
        f"Тариф: {_tier_label(tier)}\n\n"
        f"Ссылка подписки:\n{sub_url}\n\n"
        "Скопируй ссылку → открой Hiddify → нажми + → вставь.\n\n"
        f"{_configs_text(tier)}",
        keyboard=tunnel_detail_kb(tunnel.id, tier)
    )
    await _send_qr(message, sub_url, api, upload)


async def cmd_tunnel_key(message: Message, tunnel_id: int, api, upload):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)

    if not t or t.user_id != user.id:
        await message.answer("Туннель не найден.", keyboard=main_menu_kb())
        return

    tier = t.tier or "standard"
    if t.key_id:
        sub_url = _sub_url(t.key_id)
        await message.answer(
            f"🔑 {t.label or 'Туннель'}\n\n"
            f"Ссылка подписки:\n{sub_url}\n\n"
            "Скопируй ссылку → открой Hiddify → нажми + → вставь.\n\n"
            f"{_configs_text(tier)}\n\n"
            "Конфиги не обновляются? Нажми обновить рядом с группой в приложении.",
            keyboard=tunnel_detail_kb(tunnel_id, tier)
        )
    elif t.key_string:
        await message.answer(
            f"🔑 {t.label or 'Туннель'}\n\n"
            f"{t.key_string}\n\n"
            "Скопируй и вставь в Hiddify.",
            keyboard=tunnel_detail_kb(tunnel_id, tier)
        )
    else:
        await message.answer("❌ Ключ не найден.", keyboard=back_kb())


async def cmd_tunnel_regen(message: Message, tunnel_id: int, api, upload):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
    if not t or t.user_id != user.id:
        await message.answer("Туннель не найден.", keyboard=main_menu_kb())
        return

    await message.answer("⏳ Обновляю конфигурацию...")

    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
        if not t:
            await message.answer("❌ Туннель не найден.", keyboard=back_kb())
            return
        tier = t.tier or "standard"
        old_node_id = t.node_id
        old_key_id = t.key_id
        old_key_id_2 = t.key_id_2
        old_key_id_3 = t.key_id_3
        old_key_id_4 = t.key_id_4

    # Удаляем старый ключ и создаём новый без открытой DB сессии
    if old_node_id and old_key_id:
        try:
            await node_manager.delete_key(old_node_id, old_key_id, old_key_id_2, old_key_id_3, old_key_id_4)
        except Exception:
            pass
    try:
        key_data = await node_manager.create_key(node_id=old_node_id, tier=tier)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", keyboard=back_kb())
        return

    try:
        async with managed_session() as db:
            t = await db.get(Tunnel, tunnel_id)
            if not t:
                await message.answer("❌ Туннель не найден.", keyboard=back_kb())
                return
            t.key_id = key_data["key_id"]
            t.key_id_2 = key_data.get("key_id_2")
            t.key_id_3 = key_data.get("key_id_3")
            t.key_id_4 = key_data.get("key_id_4")
            t.node_id = key_data["node_id"]
            t.key_string = key_data["key_string"]
            t.sub_links = json.dumps(key_data["sub_links"]) if key_data.get("sub_links") else None
            await db.commit()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", keyboard=back_kb())
        return

    new_sub_url = _sub_url(key_data["key_id"])
    await message.answer(
        "✅ Конфигурация обновлена!\n\n"
        f"Ссылка подписки:\n{new_sub_url}\n\n"
        "Обнови подписку в Hiddify — нажми кнопку обновления рядом с группой.\n\n"
        f"{_configs_text(tier)}",
        keyboard=tunnel_detail_kb(tunnel_id, tier)
    )


async def cmd_tunnel_delete_confirm(message: Message, tunnel_id: int):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
    if not t or t.user_id != user.id:
        await message.answer("Туннель не найден.", keyboard=main_menu_kb())
        return
    await message.answer(
        f"🗑 Удалить {t.label or 'Туннель'}?\n\nКлюч перестанет работать. Это действие необратимо.",
        keyboard=delete_confirm_kb(tunnel_id)
    )


async def cmd_tunnel_delete(message: Message, tunnel_id: int):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
        if not t or t.user_id != user.id:
            await message.answer("Туннель не найден.", keyboard=main_menu_kb())
            return

        # Защита от бесплатного VPN через удаление
        today = date.today()
        already_charged = await db.scalar(
            select(DailyCharge).where(
                DailyCharge.user_id == user.id,
                DailyCharge.date == today,
            )
        )
        if not already_charged:
            active_result = await db.execute(
                select(Tunnel).where(Tunnel.user_id == user.id, Tunnel.active == True)
            )
            active_tunnels = active_result.scalars().all()
            if active_tunnels:
                daily_cost = _tunnel_daily_cost(active_tunnels)
                user_obj = await db.get(User, user.id)
                user_obj.balance = round(max(0.0, user_obj.balance - daily_cost), 2)
                db.add(DailyCharge(
                    user_id=user.id,
                    amount=daily_cost,
                    devices=len(active_tunnels),
                    date=today,
                ))

        label = t.label
        node_id = t.node_id
        key_ids = (t.key_id, t.key_id_2, t.key_id_3, t.key_id_4)
        wg_private_key = t.wg_private_key
        await db.delete(t)
        await db.commit()

    try:
        if node_id and key_ids[0]:
            await node_manager.delete_key(node_id, *key_ids, wg_private_key=wg_private_key)
    except Exception:
        pass

    await message.answer("✅ Устройство удалено.", keyboard=main_menu_kb())


async def cmd_tunnel_tier_switch(message: Message, tunnel_id: int):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
    if not t or t.user_id != user.id:
        await message.answer("Туннель не найден.", keyboard=main_menu_kb())
        return
    if not t.active:
        await message.answer(
            "Туннель отключён — пополните баланс для переключения тарифа.",
            keyboard=main_menu_kb()
        )
        return

    current_tier = t.tier or "standard"
    new_tier = "standard" if current_tier == "tor" else "tor"
    new_rate = settings.device_daily_rate if new_tier == "standard" else settings.tor_daily_rate

    await message.answer(
        f"🔄 Переключить тариф?\n\n"
        f"Текущий: {_tier_label(current_tier)}\n"
        f"Новый: {_tier_label(new_tier)} (${new_rate}/день)\n\n"
        "⚠️ Ключ будет пересоздан — нужно переподключить VPN в приложении.",
        keyboard=tier_switch_confirm_kb(tunnel_id)
    )


async def cmd_tunnel_tier_switch_confirm(message: Message, tunnel_id: int, api, upload):
    vk_id = message.from_id
    user, _ = await get_or_create_user(vk_id)

    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
    if not t or t.user_id != user.id:
        await message.answer("Туннель не найден.", keyboard=main_menu_kb())
        return

    current_tier = t.tier or "standard"
    new_tier = "standard" if current_tier == "tor" else "tor"
    new_rate = settings.device_daily_rate if new_tier == "standard" else settings.tor_daily_rate

    if user.balance < new_rate:
        await message.answer(
            f"❌ Недостаточно баланса. Нужно минимум ${new_rate:.2f}.",
            keyboard=main_menu_kb()
        )
        return

    await message.answer("⏳ Переключаю тариф...")

    # Читаем данные, закрываем сессию до обращения к Marzban
    async with managed_session() as db:
        t = await db.get(Tunnel, tunnel_id)
        if not t:
            await message.answer("❌ Туннель не найден.", keyboard=back_kb())
            return
        tunnel_label = t.label
        old_node_id = t.node_id
        old_key_id = t.key_id
        old_key_id_2 = t.key_id_2
        old_key_id_3 = t.key_id_3
        old_key_id_4 = t.key_id_4

        today = date.today()
        already_charged = await db.scalar(
            select(DailyCharge).where(
                DailyCharge.user_id == t.user_id,
                DailyCharge.date == today,
            )
        )
        user_id = t.user_id

    # Вызовы Marzban без открытой DB сессии
    if old_key_id and old_node_id:
        try:
            await node_manager.delete_key(old_node_id, old_key_id, old_key_id_2, old_key_id_3, old_key_id_4)
        except Exception:
            pass
    try:
        key_data = await node_manager.create_key(node_id=old_node_id, tier=new_tier)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", keyboard=back_kb())
        return

    try:
        async with managed_session() as db:
            t = await db.get(Tunnel, tunnel_id)
            if not t:
                await message.answer("❌ Туннель не найден.", keyboard=back_kb())
                return
            user_obj = await db.get(User, user_id)

            old_rate = settings.tor_daily_rate if current_tier == "tor" else settings.device_daily_rate
            if already_charged and new_rate > old_rate:
                diff = round(new_rate - old_rate, 4)
                user_obj.balance = round(max(0.0, user_obj.balance - diff), 2)

            t.key_id = key_data["key_id"]
            t.key_id_2 = key_data.get("key_id_2")
            t.key_id_3 = key_data.get("key_id_3")
            t.key_id_4 = key_data.get("key_id_4")
            t.node_id = key_data["node_id"]
            t.key_string = key_data["key_string"]
            t.sub_links = json.dumps(key_data["sub_links"]) if key_data.get("sub_links") else None
            t.tier = new_tier
            await db.commit()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", keyboard=back_kb())
        return

    new_sub_url = _sub_url(key_data["key_id"])
    await message.answer(
        f"✅ {tunnel_label} — тариф переключён!\n"
        f"Тариф: {_tier_label(new_tier)}\n\n"
        f"Ссылка подписки:\n{new_sub_url}\n\n"
        "Обнови подписку в Hiddify.\n\n"
        f"{_configs_text(new_tier)}",
        keyboard=tunnel_detail_kb(tunnel_id, new_tier)
    )
