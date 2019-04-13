import argparse
from bot_core import KeyClassificator
from email_data_json import Base_

test_str = u'Подключите услугу «Командировка» на номере\n'\
    u'1271132111 кодовое слово: Слон и Моська'
test_str2 = u'Подключите услугу «Роуминг Гудбай»\n'\
    u'1271132111\n\n'\
    u'Слон'

if __name__ == "__main__":
    # get_messages
    messages = Base_.get_messages()
    for message in messages:
        print(message)
        # analize or skip
        # add key in base
        # add key to frontend
    classificator = KeyClassificator()
    print(classificator.find_all(test_str))
    print(classificator.find_all(test_str2))

