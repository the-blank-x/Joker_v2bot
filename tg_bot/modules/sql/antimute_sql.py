import threading

from sqlalchemy import String, Column, Integer

from tg_bot.modules.sql import SESSION, BASE

DEF_COUNT = 0
DEF_LIMIT = 0
DEF_OBJ = (None, DEF_COUNT, DEF_LIMIT)

class AntimuteControl(BASE):
    __tablename__ = "antimute"
    chat_id = Column(String(14), primary_key=True)
    user_id = Column(Integer)
    count = Column(Integer, default=DEF_COUNT)
    limit = Column(Integer, default=DEF_LIMIT)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)  # ensure string

    def __repr__(self):
        return "<Antimute control for %s>" % self.chat_id


AntimuteControl.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()

CHAT_ANTIMUTE = {}


def set_antimute(chat_id, amount):
    with INSERTION_LOCK:
        antimute = SESSION.query(AntimuteControl).get(str(chat_id))
        if not antimute:
            antimute = AntimuteControl(str(chat_id))

        antimute.user_id = None
        antimute.limit = amount

        CHAT_ANTIMUTE[str(chat_id)] = (None, DEF_COUNT, amount)

        SESSION.add(antimute)
        SESSION.commit()


def update_antimute(chat_id: str, user_id) -> bool:
    if str(chat_id) in CHAT_ANTIMUTE:
        curr_user_id, count, limit = CHAT_ANTIMUTE.get(str(chat_id), DEF_OBJ)

        if limit == 0:  # no antimute
            return False

        if user_id != curr_user_id or user_id is None:  # other user
            CHAT_ANTIMUTE[str(chat_id)] = (user_id, DEF_COUNT, limit)
            return False

        count += 1
        if count > limit:  # too many msgs, kick
            CHAT_ANTIMUTE[str(chat_id)] = (None, DEF_COUNT, limit)
            return True

        # default -> update
        CHAT_ANTIMUTE[str(chat_id)] = (user_id, count, limit)
        return False


def get_antimute_limit(chat_id):
    return CHAT_ANTIMUTE.get(str(chat_id), DEF_OBJ)[2]


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        antiflood = SESSION.query(AntimuteControl).get(str(old_chat_id))
        if antimute:
            CHAT_ANTIMUTE[str(new_chat_id)] = CHAT_ANTIMUTE.get(str(old_chat_id), DEF_OBJ)
            antimute.chat_id = str(new_chat_id)
            SESSION.commit()

        SESSION.close()


def __load_antimute_settings():
    global CHAT_ANTIMUTE
    try:
        all_chats = SESSION.query(AntimuteControl).all()
        CHAT_ANTIMUTE = {chat.chat_id: (None, DEF_COUNT, chat.limit) for chat in all_chats}
    finally:
        SESSION.close()


__load_antimute_settings()
