import argparse
from bot_core import Speak, Base_
import smtplib
import re
import os

top_dir = '/home/a0231165/domains/cometbot.ru/pyscript'
os.chdir(top_dir)

if __name__ == "__main__":
    base = Base_()
    messages = base.select_json('messages')
    base = Base_()
    lines = base.select_json('lastpipelines')
    server = 'smtp.cometbot.ru'
    user = 'megabot@cometbot.ru'
    password = 'megabotiscool'
    session = smtplib.SMTP(server)
        # if your SMTP server doesn't need authentications,
        # you don't need the following line:
    session.login(user, password)

    for message in messages:
        mail_mask = re.compile(r"[a-zA-Z._\-0-9]+@[a-zA-Z._\-0-9]+")
        email = mail_mask.findall(message["sender"])[0]
        speaking = Speak(email, session)  # create speak thread
        speaking.send_response(message)

    Base_.clean_table_messages()
    print('\n\n\n')
    # base.clean_base("messages")
