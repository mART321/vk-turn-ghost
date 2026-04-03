"""VK клавиатуры для GhostMode бота."""
from vkbottle import Keyboard, Text, OpenLink, EMPTY_KEYBOARD

HIDDIFY_ANDROID = "https://play.google.com/store/apps/details?id=app.hiddify.com"
HIDDIFY_IOS     = "https://apps.apple.com/app/hiddify-proxy-vpn/id6596777532"
HIDDIFY_WINDOWS = "https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-Windows-Setup-x64.exe"
HIDDIFY_MACOS   = "https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-MacOS.dmg"
V2BOX_IOS       = "https://apps.apple.com/app/v2box-v2ray-client/id6446814690"


def main_menu_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📡 Мой VPN", payload={"cmd": "tunnels"}))
    kb.add(Text("💳 Пополнить", payload={"cmd": "topup"}))
    kb.row()
    kb.add(Text("💰 Баланс", payload={"cmd": "balance"}))
    kb.add(Text("👥 Рефералка", payload={"cmd": "referral"}))
    kb.row()
    kb.add(Text("📖 Как пользоваться", payload={"cmd": "howto"}))
    kb.add(Text("❓ Частые вопросы", payload={"cmd": "faq"}))
    kb.row()
    kb.add(Text("🔑 Обход белых списков", payload={"cmd": "turn"}))
    kb.add(Text("🔗 Синхр. с Telegram", payload={"cmd": "sync_tg"}))
    return kb.get_json()


def back_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def tunnel_list_kb(tunnels: list) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for t in tunnels:
        status = "🟢" if t.active else "🔴"
        kb.add(Text(f"{status} {t.label or 'Туннель'}", payload={"cmd": "tunnel_info", "id": t.id}))
        kb.row()
    kb.add(Text("➕ Добавить устройство", payload={"cmd": "create_tunnel"}))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def device_type_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📱 iPhone", payload={"cmd": "tunnel_device", "device": "iPhone"}))
    kb.add(Text("🤖 Android", payload={"cmd": "tunnel_device", "device": "Android"}))
    kb.row()
    kb.add(Text("💻 Mac", payload={"cmd": "tunnel_device", "device": "Mac"}))
    kb.add(Text("🖥 Windows", payload={"cmd": "tunnel_device", "device": "Windows"}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "tunnels"}))
    return kb.get_json()


def tariff_kb(device: str) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⚡ Fast — ~$3/мес", payload={"cmd": "tunnel_tier", "device": device, "tier": "standard"}))
    kb.row()
    kb.add(Text("🧅 Ghost — ~$6/мес", payload={"cmd": "tunnel_tier", "device": device, "tier": "tor"}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "create_tunnel"}))
    return kb.get_json()


def tunnel_detail_kb(tunnel_id: int, tier: str) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🔑 Показать ключ", payload={"cmd": "tunnel_key", "id": tunnel_id}))
    kb.row()
    kb.add(Text("🔄 Обновить ключ", payload={"cmd": "tunnel_regen", "id": tunnel_id}))
    kb.row()
    switch_label = "⬇️ Перейти на Fast" if tier == "tor" else "⬆️ Перейти на Ghost"
    kb.add(Text(switch_label, payload={"cmd": "tunnel_tier_switch", "id": tunnel_id}))
    kb.row()
    kb.add(Text("🗑 Удалить", payload={"cmd": "tunnel_delete_confirm", "id": tunnel_id}))
    kb.row()
    kb.add(Text("⬅️ К туннелям", payload={"cmd": "tunnels"}))
    return kb.get_json()


def tunnel_info_kb(tunnel_id: int, active: bool, tier: str = "standard") -> str:
    """Алиас для обратной совместимости."""
    return tunnel_detail_kb(tunnel_id, tier)


def delete_confirm_kb(tunnel_id: int) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("✅ Да, удалить", payload={"cmd": "tunnel_delete", "id": tunnel_id}))
    kb.add(Text("❌ Отмена", payload={"cmd": "tunnel_info", "id": tunnel_id}))
    return kb.get_json()


def tier_switch_confirm_kb(tunnel_id: int) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("✅ Переключить", payload={"cmd": "tunnel_tier_switch_confirm", "id": tunnel_id}))
    kb.add(Text("❌ Отмена", payload={"cmd": "tunnel_info", "id": tunnel_id}))
    return kb.get_json()


def topup_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📱 Оплата через СБП", payload={"cmd": "topup_sbp"}))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def cryptobot_amount_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    for a in [5, 10, 20, 50]:
        kb.add(Text(f"${a}", payload={"cmd": "cryptobot_amount", "amount": a}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "topup"}))
    return kb.get_json()


def sbp_amount_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    for a in [3, 6, 12]:
        kb.add(Text(f"${a}", payload={"cmd": "sbp_amount", "amount": a}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "topup"}))
    return kb.get_json()


def cryptobot_invoice_kb(pay_url: str, payment_id: int) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(pay_url, "💎 Оплатить в CryptoBot"))
    kb.row()
    kb.add(Text("✅ Я оплатил", payload={"cmd": "check_payment", "id": payment_id}))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "topup"}))
    return kb.get_json()


def sbp_invoice_kb(confirmation_url: str) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(confirmation_url, "📱 Открыть QR-код"))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "topup"}))
    return kb.get_json()


def howto_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(HIDDIFY_ANDROID, "🤖 Android — Hiddify"))
    kb.row()
    kb.add(Text("🍎 iPhone — выбрать приложение", payload={"cmd": "howto_iphone"}))
    kb.row()
    kb.add(OpenLink(HIDDIFY_WINDOWS, "🪟 Windows — Hiddify"))
    kb.row()
    kb.add(Text("🍏 macOS — инструкция", payload={"cmd": "howto_macos"}))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def howto_iphone_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(HIDDIFY_IOS, "⭐ Hiddify (рекомендуем)"))
    kb.row()
    kb.add(OpenLink(V2BOX_IOS, "V2Box"))
    kb.row()
    kb.add(OpenLink("https://apps.apple.com/app/streisand/id6450534064", "Streisand"))
    kb.row()
    kb.add(OpenLink("https://apps.apple.com/app/foxray/id6448898396", "Foxray"))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "howto"}))
    return kb.get_json()


def howto_macos_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(HIDDIFY_MACOS, "⬇️ Скачать Hiddify для macOS"))
    kb.row()
    kb.add(Text("⬅️ Назад", payload={"cmd": "howto"}))
    return kb.get_json()


def about_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📱 Подключиться", payload={"cmd": "tunnels"}))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def faq_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📶 VPN перестал работать", payload={"cmd": "faq_broken"}))
    kb.row()
    kb.add(Text("🔑 Ключ не добавляется", payload={"cmd": "faq_key"}))
    kb.row()
    kb.add(Text("💰 Не вижу зачисления", payload={"cmd": "faq_payment"}))
    kb.row()
    kb.add(Text("💸 Почему списывается баланс?", payload={"cmd": "faq_charge"}))
    kb.row()
    kb.add(Text("🔗 GhostMode в VK", payload={"cmd": "faq_vk"}))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def faq_item_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⬅️ К вопросам", payload={"cmd": "faq"}))
    kb.row()
    kb.add(Text("🏠 Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def turn_kb(oauth_url: str) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(OpenLink(oauth_url, "Открыть страницу VK"))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def turn_success_kb() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()


def turn_menu_kb() -> str:
    """Клавиатура раздела обхода белых списков."""
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📋 Получить ссылку для приложения", payload={"cmd": "turn_get_link"}))
    kb.row()
    kb.add(Text("⬅️ Главное меню", payload={"cmd": "menu"}))
    return kb.get_json()
