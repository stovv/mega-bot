import argparse
from bot_core import KeyParser, Base_, DocumentReader, TextClassifier

test_str = u'Подключите услугу «Командировка» на номере\n'\
    u'1271132111 кодовое слово: Слон и Моська'
test_str2 = u'Подключите услугу «Роуминг Гудбай»\n'\
    u'1271132111\n\n'\
    u'Слон'

if __name__ == "__main__":
    # get_messages
    parsed = {}
    messages = Base_.select_json('messages')
    users = Base_.select_json("users")
    for message in messages:
        sender = message['sender']
        print(message["body"])
        # get lk_number from text or attach
        # check access email and sender_email
        # parse
        # add parse data to parsed
        # add status to parsed
    Base_.clean_base("messages")
    # push parsed base

