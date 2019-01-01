import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antimute_sql as sql

ANTIMUTE_GROUP = 3


@run_async
@loggable
def check_antimute(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_antimute(chat.id, None)
        return ""

    should_mute = sql.update_antimute(chat.id, user.id)
    if not should_mute:
        return ""

    try:
        bot.restrict_chat_member(chat.id, user.id, can_send_messages=False)
        msg.reply_text("Go Away nigga")

        return "<b>{}:</b>" \
               "\n#mutED" \
               "\n<b>User:</b> {}" \
               "\nSPAMMED the group.".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("I can't mute people here, give me permissions first! Until then, I'll disable antimute.")
        sql.set_antimute(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFO" \
               "\nDon't have mute permissions, so automatically disabled antimute.".format(chat.title)


@run_async
@user_admin
@can_restrict
@loggable
def set_antimute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_antimute(chat.id, 0)
            message.reply_text("Antimute has been disabled.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_antimute(chat.id, 0)
                message.reply_text("Antimute has been disabled.")
                return "<b>{}:</b>" \
                       "\n#SETANTIMUTE" \
                       "\n<b>Admin:</b> {}" \
                       "\nDisabled antimutr.".format(html.escape(chat.title), mention_html(user.id, user.first_name))

            elif amount < 3:
                message.reply_text("Antimute has to be either 0 (disabled), or a number bigger than 3!")
                return ""

            else:
                sql.set_antimute(chat.id, amount)
                message.reply_text("Antimute has been updated and set to {}".format(amount))
                return "<b>{}:</b>" \
                       "\n#SETANTIMUTE" \
                       "\n<b>Admin:</b> {}" \
                       "\nSet antimute to <code>{}</code>.".format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("Unrecognised argument - please use a number, 'off', or 'no'.")

    return ""


@run_async
def antimute(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    limit = sql.get_antimute_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text("I'm not currently enforcing antimute control!")
    else:
        update.effective_message.reply_text(
            "I'm currently muting users if they send more than {} consecutive messages.".format(limit))


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_antimute_limit(chat_id)
    if limit == 0:
        return "*Not* currently enforcing antimute control."
    else:
        return "Antimute is set to `{}` messages.".format(limit)


__help__ = """
 - /antimute: Get the current flood control setting

*Admin only:*
 - /setantimute <int/'no'/'off'>: enables or disables flood control
"""

__mod_name__ = "AntiMute"

ANTIMUTE_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_antimute)
SET_ANTIMUTE_HANDLER = CommandHandler("setantimute", set_antimute, pass_args=True, filters=Filters.group)
ANTIMUTE_HANDLER = CommandHandler("antimute", antimute, filters=Filters.group)

dispatcher.add_handler(ANTIMUTE_BAN_HANDLER, ANTIMUTE_GROUP)
dispatcher.add_handler(SET_ANTIMUTE_HANDLER)
dispatcher.add_handler(ANTIMUTE_HANDLER)
