"""GhostMode VK Bot — entry point."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vkbottle.bot import Bot, Message
from vkbottle.dispatch.rules.base import ABCRule, PayloadRule
from vkbottle.tools.mini_types.base import BaseMessageMin


class CmdRule(ABCRule[BaseMessageMin]):
    """Матчит кнопки только по полю cmd, игнорируя остальные поля payload."""
    def __init__(self, cmd: str):
        self.cmd = cmd

    async def check(self, event: BaseMessageMin) -> bool:
        payload = event.get_payload_json()
        if isinstance(payload, dict):
            return payload.get("cmd") == self.cmd
        return False

from config import settings
from db.database import init_db
from services.node_manager import node_manager

from vk_bot.handlers import start, tunnel, balance, referral, faq, turn, sync
from vk_bot.handlers import about, howto
from vk_bot.handlers.turn import TOKEN_RE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.vk_token)


@bot.error_handler.register_error_handler(Exception)
async def on_error(e: Exception):
    logger.error(f"Handler error: {type(e).__name__}: {e}", exc_info=True)


def _get_upload():
    from vkbottle.tools import PhotoMessageUploader
    return PhotoMessageUploader(bot.api)


# ─── Start / Menu ─────────────────────────────────────────────────────────────

@bot.on.message(text=["Начать", "начать", "/start", "start"])
async def on_start(message: Message):
    await start.cmd_start(message)


@bot.on.message(CmdRule("menu"))
async def on_menu(message: Message):
    await start.cmd_menu(message)


@bot.on.message(CmdRule("balance"))
async def on_balance(message: Message):
    await start.cmd_balance(message)


@bot.on.message(CmdRule("merge_confirm"))
async def on_merge_confirm(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await start.cmd_merge_confirm(message, payload.get("tg_uid"), payload.get("vk_id"))


# ─── О сервисе / Инструкция ───────────────────────────────────────────────────

@bot.on.message(CmdRule("about"))
async def on_about(message: Message):
    await about.cmd_about(message)


@bot.on.message(CmdRule("howto"))
async def on_howto(message: Message):
    await howto.cmd_howto(message)


@bot.on.message(CmdRule("howto_iphone"))
async def on_howto_iphone(message: Message):
    await howto.cmd_howto_iphone(message)


@bot.on.message(CmdRule("howto_macos"))
async def on_howto_macos(message: Message):
    await howto.cmd_howto_macos(message)


# ─── Туннели ──────────────────────────────────────────────────────────────────

@bot.on.message(CmdRule("tunnels"))
async def on_tunnels(message: Message):
    await tunnel.cmd_tunnels(message)


@bot.on.message(CmdRule("tunnel_info"))
async def on_tunnel_info(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_info(message, payload.get("id"))


@bot.on.message(CmdRule("create_tunnel"))
async def on_create_tunnel(message: Message):
    await tunnel.cmd_create_tunnel(message)


@bot.on.message(CmdRule("tunnel_device"))
async def on_tunnel_device(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_device(message, payload.get("device", "iPhone"))


@bot.on.message(CmdRule("tunnel_tier"))
async def on_tunnel_tier(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_tier(
        message,
        payload.get("device", "iPhone"),
        payload.get("tier", "standard"),
        bot.api,
        _get_upload(),
    )


@bot.on.message(CmdRule("tunnel_key"))
async def on_tunnel_key(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_key(message, payload.get("id"), bot.api, _get_upload())


@bot.on.message(CmdRule("tunnel_regen"))
async def on_tunnel_regen(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_regen(message, payload.get("id"), bot.api, _get_upload())


@bot.on.message(CmdRule("tunnel_tier_switch"))
async def on_tunnel_tier_switch(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_tier_switch(message, payload.get("id"))


@bot.on.message(CmdRule("tunnel_tier_switch_confirm"))
async def on_tunnel_tier_switch_confirm(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_tier_switch_confirm(
        message, payload.get("id"), bot.api, _get_upload()
    )


@bot.on.message(CmdRule("tunnel_delete_confirm"))
async def on_tunnel_delete_confirm(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_delete_confirm(message, payload.get("id"))


@bot.on.message(CmdRule("tunnel_delete"))
async def on_tunnel_delete(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await tunnel.cmd_tunnel_delete(message, payload.get("id"))


# ─── Баланс / Пополнение ──────────────────────────────────────────────────────

@bot.on.message(CmdRule("topup"))
async def on_topup(message: Message):
    await balance.cmd_topup(message)


@bot.on.message(CmdRule("topup_sbp"))
async def on_topup_sbp(message: Message):
    await balance.cmd_topup_sbp(message)


@bot.on.message(CmdRule("sbp_amount"))
async def on_sbp_amount(message: Message):
    import json as _json
    payload = _json.loads(message.payload or "{}")
    await balance.cmd_topup_sbp_amount(message, payload.get("amount", 10))


# ─── Рефералка ────────────────────────────────────────────────────────────────

@bot.on.message(CmdRule("referral"))
async def on_referral(message: Message):
    await referral.cmd_referral(message)


# ─── FAQ ──────────────────────────────────────────────────────────────────────

@bot.on.message(CmdRule("faq"))
async def on_faq(message: Message):
    await faq.cmd_faq(message)


@bot.on.message(CmdRule("faq_broken"))
async def on_faq_broken(message: Message):
    await faq.cmd_faq_item(message, "faq_broken")


@bot.on.message(CmdRule("faq_key"))
async def on_faq_key(message: Message):
    await faq.cmd_faq_item(message, "faq_key")


@bot.on.message(CmdRule("faq_payment"))
async def on_faq_payment(message: Message):
    await faq.cmd_faq_item(message, "faq_payment")


@bot.on.message(CmdRule("faq_charge"))
async def on_faq_charge(message: Message):
    await faq.cmd_faq_item(message, "faq_charge")


@bot.on.message(CmdRule("faq_vk"))
async def on_faq_vk(message: Message):
    await faq.cmd_faq_item(message, "faq_vk")


# ─── TURN ─────────────────────────────────────────────────────────────────────

@bot.on.message(CmdRule("turn"))
async def on_turn(message: Message):
    await turn.cmd_turn(message)


@bot.on.message(CmdRule("turn_get_link"))
async def on_turn_get_link(message: Message):
    await turn.cmd_turn_get_link(message)


# ─── Синхронизация TG ─────────────────────────────────────────────────────────

@bot.on.message(CmdRule("sync_tg"))
async def on_sync_tg(message: Message):
    await sync.cmd_sync_tg(message)


# ─── Catch-all ────────────────────────────────────────────────────────────────

@bot.on.message()
async def on_any_message(message: Message):
    text = message.text or ""
    logger.info(f"CATCH-ALL: text={text!r} payload={message.payload!r} payload_json={message.get_payload_json()!r}")
    if TOKEN_RE.search(text) or text.startswith("vk1.a."):
        handled = await turn.handle_oauth_url(message)
        if handled:
            return
    await start.cmd_start(message)


# ─── Запуск ───────────────────────────────────────────────────────────────────

async def startup():
    for attempt in range(5):
        try:
            await init_db()
            break
        except Exception as e:
            if attempt < 4:
                logger.warning(f"init_db attempt {attempt+1} failed: {e}, retrying...")
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error(f"init_db failed after 5 attempts: {e}")
                raise
    logger.info("БД инициализирована")
    await node_manager.login_all()
    logger.info("Node Manager готов")
    logger.info("VK бот запускается...")


if __name__ == "__main__":
    async def main():
        await startup()
        bot.loop_wrapper.loop = asyncio.get_event_loop()
        bot.loop_wrapper._running = True
        await bot.run_polling()

    asyncio.run(main())
