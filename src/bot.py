import logging
from functools import wraps
from typing import Callable, Iterable, List, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.api import GroupFactoryApi
from src.config import Config


logger = logging.getLogger(__name__)

NEWGRP_NAME, NEWGRP_DESCRIPTION, NEWGRP_CONFIRM = range(3)
QR_IMAGE = 10


HELP_TEXT = """GroupFactory client bot

Group creation:
/newgrp - start guided group creation
/get_group <group_id>
/group_add_users <group_id> <user_id> ...

Default users:
/get_users
/set_users <id_or_username_or_id:username> ...
/add_users <id_or_username_or_id:username> ...
/remove_users <id_or_username_or_id:username> ...
/add_user <username_or_id:username>

QR configs:
/get_qr [qr_group]
/set_qr <payload>
/set_qr <qr_group> <payload>
/set_qr_group <qr_group> - forward a .importbackup QR image
/qr_groups [qr_group]
/qr_group_add <qr_group> <telegram_group_id> ...
/qr_group_remove <telegram_group_id> ...
/sync_qr [qr_group|all]

Other:
/users - list database users
/user <user_id>
/delete_user <user_id>
/ping
/cancel
"""


def _api(context: ContextTypes.DEFAULT_TYPE) -> GroupFactoryApi:
    return context.application.bot_data["api"]


def _config(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.application.bot_data["config"]


def _is_allowed(update: Update, config: Config) -> bool:
    if not config.allowed_chat_ids:
        return True
    chat = update.effective_chat
    return bool(chat and chat.id in config.allowed_chat_ids)


def require_allowed(handler: Callable):
    @wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_allowed(update, _config(context)):
            if update.effective_message:
                await update.effective_message.reply_text("This bot is not enabled for this chat.")
            return ConversationHandler.END
        return await handler(update, context)

    return wrapped


async def _reply(update: Update, text: str):
    message = update.effective_message
    if not message:
        return
    text = text or "No response."
    for start in range(0, len(text), 3900):
        await message.reply_text(text[start:start + 3900])


def _require_args(context: ContextTypes.DEFAULT_TYPE, usage: str) -> Optional[List[str]]:
    args = list(context.args or [])
    if not args:
        return None
    return args


def _parse_ints(values: Iterable[str]) -> List[int]:
    return [int(value.strip().rstrip(",")) for value in values if value.strip().rstrip(",")]


@require_allowed
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, HELP_TEXT)


@require_allowed
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, HELP_TEXT)


@require_allowed
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, "PONG - GroupFactory Client Bot")


@require_allowed
async def get_default_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, await _api(context).default_users())


@require_allowed
async def set_default_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/set_users <id_or_username_or_id:username> ...")
    if not args:
        await _reply(update, "Usage: /set_users <id_or_username_or_id:username> ...")
        return
    await _reply(update, await _api(context).set_default_users(args))


@require_allowed
async def add_default_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/add_users <id_or_username_or_id:username> ...")
    if not args:
        await _reply(update, "Usage: /add_users <id_or_username_or_id:username> ...")
        return
    await _reply(update, await _api(context).add_default_users(args))


@require_allowed
async def remove_default_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/remove_users <id_or_username_or_id:username> ...")
    if not args:
        await _reply(update, "Usage: /remove_users <id_or_username_or_id:username> ...")
        return
    await _reply(update, await _api(context).remove_default_users(args))


@require_allowed
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/add_user <username_or_id:username>")
    if not args:
        await _reply(update, "Usage: /add_user <username_or_id:username>")
        return
    await _reply(update, await _api(context).add_user(" ".join(args)))


@require_allowed
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, await _api(context).list_users())


@require_allowed
async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/user <user_id>")
    if not args:
        await _reply(update, "Usage: /user <user_id>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await _reply(update, "User ID must be numeric.")
        return
    await _reply(update, await _api(context).get_user(user_id))


@require_allowed
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/delete_user <user_id>")
    if not args:
        await _reply(update, "Usage: /delete_user <user_id>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await _reply(update, "User ID must be numeric.")
        return
    await _reply(update, await _api(context).delete_user(user_id))


@require_allowed
async def get_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/get_group <group_id>")
    if not args:
        await _reply(update, "Usage: /get_group <group_id>")
        return
    await _reply(update, await _api(context).get_group(args[0]))


@require_allowed
async def group_add_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/group_add_users <group_id> <user_id> ...")
    if not args or len(args) < 2:
        await _reply(update, "Usage: /group_add_users <group_id> <user_id> ...")
        return
    try:
        user_ids = _parse_ints(args[1:])
    except ValueError:
        await _reply(update, "User IDs must be numeric for group invites.")
        return
    await _reply(update, await _api(context).add_users_to_group(args[0], user_ids))


@require_allowed
async def newgrp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = (update.effective_message.text or "").strip()
    if raw_text.lower().startswith("!newgrp"):
        text = raw_text[len("!newgrp"):].strip()
    else:
        text = " ".join(context.args or []).strip()
    context.user_data.pop("newgrp", None)
    context.user_data["newgrp"] = {}

    if "|" in text:
        name, description = [item.strip() for item in text.split("|", 1)]
        if name and description:
            context.user_data["newgrp"] = {"name": name, "description": description}
            await _reply(update, _newgrp_summary(name, description))
            return NEWGRP_CONFIRM

    if text:
        context.user_data["newgrp"]["name"] = text
        await _reply(update, "Group name set. Send the group description.")
        return NEWGRP_DESCRIPTION

    await _reply(update, "Send the group name.")
    return NEWGRP_NAME


@require_allowed
async def newgrp_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.effective_message.text or "").strip()
    if name.lower() == "!cancel":
        return await cancel(update, context)
    if not name:
        await _reply(update, "Group name cannot be empty. Send the group name.")
        return NEWGRP_NAME
    context.user_data.setdefault("newgrp", {})["name"] = name
    await _reply(update, "Send the group description.")
    return NEWGRP_DESCRIPTION


@require_allowed
async def newgrp_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = (update.effective_message.text or "").strip()
    if description.lower() == "!cancel":
        return await cancel(update, context)
    if not description:
        await _reply(update, "Group description cannot be empty. Send the group description.")
        return NEWGRP_DESCRIPTION
    data = context.user_data.setdefault("newgrp", {})
    data["description"] = description
    await _reply(update, _newgrp_summary(data["name"], description))
    return NEWGRP_CONFIRM


def _newgrp_summary(name: str, description: str) -> str:
    return (
        "Group creation summary\n\n"
        f"Name: {name}\n"
        f"Description: {description}\n\n"
        "Send /confirm or !confirm to create it. Send /cancel or !cancel to abort."
    )


@require_allowed
async def newgrp_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.effective_message.text or "").strip().lower()
    if text in ("!cancel", "cancel", "no", "n"):
        return await cancel(update, context)
    if text not in ("/confirm", "!confirm", "confirm", "yes", "y"):
        await _reply(update, "Send /confirm or !confirm to create it, or /cancel to abort.")
        return NEWGRP_CONFIRM

    data = context.user_data.get("newgrp") or {}
    name = data.get("name")
    description = data.get("description")
    if not name or not description:
        context.user_data.pop("newgrp", None)
        await _reply(update, "Missing group data. Start again with /newgrp.")
        return ConversationHandler.END

    await _reply(update, "Creating group through GroupFactory API...")
    response = await _api(context).create_group(name, description)
    context.user_data.pop("newgrp", None)
    await _reply(update, response)
    return ConversationHandler.END


@require_allowed
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("newgrp", None)
    context.user_data.pop("qr_group", None)
    await _reply(update, "Operation canceled.")
    return ConversationHandler.END


@require_allowed
async def get_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_group = context.args[0] if context.args else "default"
    await _reply(update, await _api(context).get_qr(qr_group))


@require_allowed
async def set_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = list(context.args or [])
    if not args:
        context.user_data["qr_group"] = "default"
        await _reply(update, "Forward the original .importbackup QR image for default.")
        return QR_IMAGE

    if len(args) == 1:
        qr_group = "default"
        qr_data = args[0]
    else:
        qr_group = args[0]
        qr_data = " ".join(args[1:])
    await _reply(update, await _api(context).set_qr(qr_data, qr_group=qr_group))
    return ConversationHandler.END


@require_allowed
async def set_qr_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/set_qr_group <qr_group>")
    if not args:
        await _reply(update, "Usage: /set_qr_group <qr_group>")
        return ConversationHandler.END
    context.user_data["qr_group"] = args[0]
    await _reply(update, f"Forward the original .importbackup QR image for {args[0]}.")
    return QR_IMAGE


def _is_importbackup_caption(update: Update) -> bool:
    text = (update.effective_message.caption or update.effective_message.text or "").strip().lower()
    return text in (".importbackup", "/importbackup")


def _is_forwarded(update: Update) -> bool:
    message = update.effective_message
    return bool(
        getattr(message, "forward_origin", None)
        or getattr(message, "forward_from", None)
        or getattr(message, "forward_from_chat", None)
        or getattr(message, "forward_sender_name", None)
    )


def _image_reference(update: Update):
    message = update.effective_message
    if message.photo:
        return message.photo[-1].file_id, "grouphelp-importbackup.jpg", "image/jpeg"
    document = message.document
    if document and (document.mime_type or "").startswith("image/"):
        return (
            document.file_id,
            document.file_name or "grouphelp-importbackup.png",
            document.mime_type,
        )
    return None


@require_allowed
async def receive_qr_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_group = context.user_data.get("qr_group", "default")
    if not _is_forwarded(update):
        await _reply(update, "Please forward the original GroupHelp QR image message.")
        return QR_IMAGE
    if not _is_importbackup_caption(update):
        await _reply(update, "Forwarded QR message must have .importbackup as its caption/body.")
        return QR_IMAGE

    image_reference = _image_reference(update)
    if not image_reference:
        await _reply(update, "Forwarded .importbackup message must contain a QR image.")
        return QR_IMAGE

    file_id, filename, content_type = image_reference
    telegram_file = await context.bot.get_file(file_id)
    image_bytes = bytes(await telegram_file.download_as_bytearray())
    response = await _api(context).set_qr_image(qr_group, image_bytes, filename, content_type)
    if response.startswith("✅"):
        context.user_data.pop("qr_group", None)
        await _reply(update, response)
        return ConversationHandler.END

    await _reply(update, response)
    return QR_IMAGE


@require_allowed
async def qr_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_group = context.args[0] if context.args else None
    await _reply(update, await _api(context).qr_groups(qr_group))


@require_allowed
async def qr_group_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/qr_group_add <qr_group> <telegram_group_id> ...")
    if not args or len(args) < 2:
        await _reply(update, "Usage: /qr_group_add <qr_group> <telegram_group_id> ...")
        return
    await _reply(update, await _api(context).assign_qr_group(args[0], args[1:]))


@require_allowed
async def qr_group_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _require_args(context, "/qr_group_remove <telegram_group_id> ...")
    if not args:
        await _reply(update, "Usage: /qr_group_remove <telegram_group_id> ...")
        return
    await _reply(update, await _api(context).remove_qr_group_assignments(args))


@require_allowed
async def sync_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_group = context.args[0] if context.args else "default"
    await _reply(update, await _api(context).sync_qr(qr_group))


def register_handlers(application: Application, config: Config):
    application.bot_data["config"] = config
    application.bot_data["api"] = GroupFactoryApi(
        config.api_base_url,
        config.api_key,
        timeout=config.request_timeout,
    )

    newgrp_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("newgrp", newgrp_start),
            MessageHandler(filters.Regex(r"^!newgrp(?:\s+.*)?$"), newgrp_start),
        ],
        states={
            NEWGRP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, newgrp_name)],
            NEWGRP_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, newgrp_description)],
            NEWGRP_CONFIRM: [
                CommandHandler("confirm", newgrp_confirm),
                MessageHandler(filters.Regex(r"^!confirm$"), newgrp_confirm),
                MessageHandler(filters.TEXT & ~filters.COMMAND, newgrp_confirm),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex(r"^!cancel$"), cancel),
        ],
    )

    qr_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("set_qr", set_qr),
            CommandHandler("set_qr_group", set_qr_group),
        ],
        states={
            QR_IMAGE: [
                MessageHandler((filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND, receive_qr_image),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex(r"^!cancel$"), cancel),
        ],
    )

    application.add_handler(newgrp_conversation)
    application.add_handler(qr_conversation)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("get_users", get_default_users))
    application.add_handler(CommandHandler("set_users", set_default_users))
    application.add_handler(CommandHandler("add_users", add_default_users))
    application.add_handler(CommandHandler("remove_users", remove_default_users))
    application.add_handler(CommandHandler("add_user", add_user))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("user", get_user))
    application.add_handler(CommandHandler("delete_user", delete_user))
    application.add_handler(CommandHandler("get_group", get_group))
    application.add_handler(CommandHandler("group_add_users", group_add_users))
    application.add_handler(CommandHandler("get_qr", get_qr))
    application.add_handler(CommandHandler("qr_groups", qr_groups))
    application.add_handler(CommandHandler("qr_group_add", qr_group_add))
    application.add_handler(CommandHandler("qr_group_remove", qr_group_remove))
    application.add_handler(CommandHandler("sync_qr", sync_qr))
