# GhostMode VK Bot

VK бот для GhostMode VPN. Позволяет пользователям VK покупать и управлять VPN-подписками.

## Деплой

Бот работает на SpamKit сервере (46.17.44.4), systemd: `ghostmode-vk.service`.

```bash
# Файлы
/opt/ghostmode-vk/

# Логи
ssh -i ~/.ssh/ghostmode root@46.17.44.4 "journalctl -u ghostmode-vk -n 50 --no-pager"

# Рестарт
ssh -i ~/.ssh/ghostmode root@46.17.44.4 "systemctl restart ghostmode-vk"
```

## Структура

Бот использует общий код из основного репозитория GhostModeVPN (config, db, services).
Запускается из `/opt/ghostmode-vk/` где лежит и основной бот.

- `main.py` — точка входа VK бота
- `keyboards.py` — VK inline клавиатуры (vkbottle)
- `vk_bot/` — хендлеры: tunnels, balance, referral, howto, faq, turn
