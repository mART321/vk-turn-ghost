from vkbottle.bot import Message
from vk_bot.keyboards import howto_kb, howto_iphone_kb, howto_macos_kb

HOWTO_TEXT = (
    "📖 Как подключиться — 4 шага\n\n"
    "1. Скачай приложение\n"
    "Рекомендуем Hiddify — работает на всех платформах и поддерживает все наши протоколы.\n"
    "Android / iPhone / Windows / macOS → кнопки ниже\n\n"
    "2. Создай устройство\n"
    "Мой VPN → Добавить устройство → выбери тариф:\n"
    "⚡ Fast — быстро и надёжно (~$3/мес)\n"
    "🧅 Ghost — полная анонимность через Tor (~$6/мес)\n\n"
    "3. Добавь в приложение\n"
    "Бот выдаст ссылку подписки. Скопируй её → открой Hiddify → нажми + → вставь.\n"
    "Приложение само загрузит все конфиги и будет их обновлять.\n\n"
    "4. Подключись\n"
    "Выбери конфиг и подключись. Готово!\n\n"
    "⏱ Timeout / X у конфигов — это нормально. "
    "Некоторые протоколы не отвечают на пинг, но работают. Просто подключись и проверь.\n\n"
    "💡 Конфиги не обновляются?\n"
    "Нажми обновить рядом с группой подписок в приложении.\n\n"
    "❓ Проблемы с подключением?\n"
    "Закройте приложение и откройте снова. "
    "Не помогло — пишите в поддержку: https://t.me/ecosystem_sos"
)

HOWTO_IPHONE_TEXT = (
    "🍎 Приложение для iPhone\n\n"
    "Рекомендуем Hiddify — поддерживает все протоколы включая новый GhostMode H2.\n\n"
    "V2Box и остальные тоже работают, но не поддерживают H2 конфиг.\n"
    "Если не нашли Hiddify — смените регион App Store на любую страну кроме РФ."
)

HOWTO_MACOS_TEXT = (
    "🍏 Hiddify для macOS\n\n"
    "Скачайте по кнопке ниже, установите как обычно.\n\n"
    "⚠️ macOS может заблокировать запуск — это стандартная защита Gatekeeper "
    "для приложений не из App Store.\n\n"
    "Чтобы разрешить запуск, откройте Терминал и введите:\n\n"
    "sudo xattr -rd com.apple.quarantine /Applications/Hiddify.app\n\n"
    "Нажмите Enter, введите пароль от Mac, снова Enter. "
    "После этого Hiddify запустится нормально."
)


async def cmd_howto(message: Message):
    await message.answer(HOWTO_TEXT, keyboard=howto_kb())


async def cmd_howto_iphone(message: Message):
    await message.answer(HOWTO_IPHONE_TEXT, keyboard=howto_iphone_kb())


async def cmd_howto_macos(message: Message):
    await message.answer(HOWTO_MACOS_TEXT, keyboard=howto_macos_kb())
