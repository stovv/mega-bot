import json
import os
import re
import smtplib
import smtplib
from email.mime.text import MIMEText
from email.header    import Header

import pymysql.cursors
import pytesseract
from flashtext.keyword import KeywordProcessor
from pdf2image import convert_from_path

# pytesseract.pytesseract.tesseract_cmd = r'tesseract'

try:
    from PIL import Image
except ImportError:
    import Image
try:
    import secret as sc
except ImportError:
    print("Please create secret.py, and add autification data")


def send_mail(snd, recipients_emails, message):
    server = 'smtp.cometbot.ru'
    user = 'megabot@cometbot.ru'
    password = 'megabotiscool'
    msg = MIMEText(message, 'plain', 'utf-8')
    msg['Subject'] = Header('From MegaBot with love', 'utf-8')
    msg['From'] = user
    msg['To'] = ", ".join(recipients_emails)

    s = smtplib.SMTP(server, 587, timeout=10)
    s.set_debuglevel(1)
    try:
        s.starttls()
        s.login(user, password)
        s.sendmail(msg['From'], recipients_emails, msg.as_string())
    finally:
        s.quit()


class KeyParser:
    def __init__(self):
        self.num_with_text = re.compile(r"номер[еау][\s:]+[0-9]{3,12}")
        self.num_only = re.compile(r"[0-9]{3,12}")

        self.code_with_text = re.compile(r"код.+\s+сло.+[:= -]+[а-яА-Я ]{3,20}")
        self.code_only = re.compile(r"[а-яА-Я ]{3,20}")

        self.service_with_text = re.compile(r"(услуг(у|и)\s+(\"|«|')[а-яА-Я ]{3,15}(\"|»|'))")
        self.service_only = re.compile(r"((\"|«|')[а-яА-Я ]{3,15}(\"|»|'))")

        self.tariff_with_text = re.compile(r"(тари(фы|ф)\s+(\"|«|')[а-яА-Я ]{3,15}(\"|»|'))")
        self.tariff_only = re.compile(r"((\"|«|')[а-яА-Я ]{3,15}(\"|»|'))")

        synonims = {}
        with open("synonims.json", "r", encoding='utf-8') as syn_file:
            synonims = json.load(syn_file)
            self.yep_key_processor = KeywordProcessor()
            for synonim in synonims['yes']:
                self.yep_key_processor.add_keyword(synonim)

            self.nope_key_processor = KeywordProcessor()
            for synonim in synonims['not']:
                self.nope_key_processor.add_keyword(synonim)

            self.on_key_processor = KeywordProcessor()
            for synonim in synonims['on']:
                self.on_key_processor.add_keyword(synonim)

            self.off_key_processor = KeywordProcessor()
            for synonim in synonims['off']:
                self.off_key_processor.add_keyword(synonim)


    def find_num(self, text):
        search_  = self.num_with_text.findall(text)
        if len(search_) > 0:
            # print(search_)
            return self.num_only.findall(search_[0])[0].rstrip().lstrip()

        search_  = self.num_only.findall(text)
        if len(search_) > 0:
            return search_[0].rstrip().lstrip()
        return None

    def find_key(self, text):
        search_  = self.code_with_text.findall(text)
        if len(search_) > 0:
            return self.code_only.findall(search_[0])[1].rstrip().lstrip()

        for line in reversed(text.splitlines()):
            search_ = self.code_only.findall(line)
            if len(search_) > 0:
                return search_[0].rstrip().lstrip()
        return None

    def find_all_commands(self, message):
        text = message['body']
        return self.find_num(text), self.find_key(text)

    def find_bool(self, message):
        keywords_found = self.yep_key_processor.extract_keywords(message['body'])
        if len(keywords_found) > 0:
            return True

        keywords_found = self.nope_key_processor.extract_keywords(message['body'])
        if len(keywords_found) > 0:
            return False
        return None

    def find_tariff(self, message):
        text = message['body']
        used = list()
        search_  = self.tariff_with_text.findall(text)[0]
        used.append(search_[0])

        keywords_found = self.on_key_processor.extract_keywords(message['body'])
        used.extend(keywords_found)
        # print(search_[0])
        if len(search_) > 0:
            tarif_name = str(search_[0])
            tarif_names = self.tariff_only.findall(tarif_name)[0]
            if len(tarif_names) > 0:
                return tarif_names[0], used
        return None, used

    def find_service_changes(self, message):
        used = list()
        text = message['body']
        service_name = None
        mode = None

        keywords_found = self.on_key_processor.extract_keywords(message['body'])
        used.extend(keywords_found)

        search_  = self.service_with_text.findall(text)[0]
        used.append(search_[0])
        #print('search_: ',search_)

        if len(search_) > 0:
            service_name = self.service_only.findall(search_[0])[0][0]

        keywords_found = self.on_key_processor.extract_keywords(message['body'])
        if len(keywords_found) > 0:
            mode=True

        keywords_found = self.off_key_processor.extract_keywords(message['body'])
        if len(keywords_found) > 0:
            mode=False
        return service_name, mode, used

class MessageClassifier:
    def __init__(self):
        self.tariff_pipeline = (0,0)
        self.service_pipeline = (0,0)
        self.truster_pipeline = (0,0)
        self.office_pipeline = (0,0)
        self.remote_pipeline = (0,0)
        self.parser = KeyParser()
        with open("errors.json", "r", encoding='utf-8') as error_file:
            self.errors = json.load(error_file)

    def __clean_used(self, text, used):
        for use_ in used:
            try:
                replace_ = re.compile(re.escape(use_), re.IGNORECASE)
                text = replace_.sub('', text)
            except: pass
        return text


    def is_tariff_changes(self, mail):
        #text
        is_tariff = False
        number = None
        secret_word = None
        where_ = 'none'

        tariff_finder, used = self.parser.find_tariff(mail)
        changed_mail = mail
        changed_mail['body'] = self.__clean_used(mail['body'], used)
        # print('changed: ', changed_mail['body'])
        if tariff_finder is not None:
            is_tariff = True
            where_ = "text"
            number, secret_word = self.parser.find_all_commands(changed_mail)
        #text

        #attach
        #attach
        return is_tariff, where_, {'number':number, 'secret':secret_word,'type':'Смена тарифа на ' + str(tariff_finder)}

    def is_service_changes(self, mail):
        #text
        is_service = False
        number = None
        secret_word = None
        on_off = None
        where_ = "none"

        service_finder, mode, used = self.parser.find_service_changes(mail)
        if mode:
            on_off = 'Подключение'
        elif not mode:
            on_off = 'Отключение'
        changed_mail = mail
        changed_mail['body'] = self.__clean_used(mail['body'], used)
        # print('changed: ', changed_mail['body'])
        if service_finder is not None:
            is_service = True
            where_ = 'text'
            number, secret_word = self.parser.find_all_commands(changed_mail)
        #text

        #attach
        #attach
        return is_service, where_, {'number':number, 'secret':secret_word, 'type':str(on_off) + ' услуг: ' + str(service_finder)}
# ------------------------------
    def is_truster(self, mail):
        pass

    def is_office(self, mail):
        pass

    def is_connect_remote(self, mail):
        pass
#-----------------------------------

    def is_bool(self, mail):
        exit_code = (self.parser.find_bool(mail))
        is_bool = False
        if exit_code != None: is_bool = True
        return is_bool, {'exit_code':exit_code}

    def is_command(self, mail):
        status = False
        number, secret_word = self.parser.find_all_commands(mail)
        if number is not None and secret_word is not None:
            status = True
        return status, {'number':number, 'secret':secret_word}


    def classify(self, mail, is_com=False):
        # classify text for:
        #                   "Создание тарифа-текст" 0.1
        #                   "Создание тарифа-аттач" 1.0
        #                   "Подключение\Отключение услуг-текст" 3.0
        #                   "Подключение\Отключение услуг-аттач" 4.0
        #                    "Ошибка" 2.2
        #                   -----------------
        #                   Переспросить кодовое слово .404
        try:
            status, where_, data = self.is_tariff_changes(mail)
            if status:
                if data['number'] != None and data['secret'] != None:
                    if where_ == 'text': return (0,1),data
                    if where_ == 'attach': return (1,0),data
                else:
                    if data['number'] != None:
                        data['error_text'] = self.errors['secret_not_find']
                        self.secret = Base_.get_secret(data['number'])
                    elif data['secret'] != None:
                        data['error_text'] = self.errors['number_not_find']
                    elif data['secret'] != self.secret: data['error_text'] = self.errors['not_valid_secret']
                    else: data['error_text'] = self.errors['secret_and_number_not_find']
                    return (2,2),data
        except: pass
        try:
            status, where_, data = self.is_service_changes(mail)
            if status:
                if data['number'] != None and data['secret'] != None:
                    if where_ == 'text': return (3,0),data
                    if where_ == 'attach': return (4,0),data
                else:
                    if data['number'] != None: data['error_text'] = self.errors['secret_not_find']
                    elif data['secret'] != None: data['error_text'] = self.errors['number_not_find']
                    else: data['error_text'] = self.errors['secret_and_number_not_find']
                    return (2,2),data
        except: pass
        if is_com:
            try:
                status, data = self.is_command(mail)
                if status:
                    return (1,0), data
            except: pass
        return None

class DocumentReader:
    def __init__(self, path):
        if type(path) is list:
            pass
        elif type(path) is str:
            filename, file_extension = os.path.splitext(path)
            if file_extension == ".pdf":
                self.__documents = self.__get_images_from_pdf(path) # get a list
            if file_extension == ".png" or file_extension == ".jpg":
                self.__documents = [Image.open(path)]

    def __get_images_from_pdf(self, path):
        pages = convert_from_path(path, 500)
        return pages


    def __contrastor(self, img, level):
        factor = (259 * (level + 255)) / (255 * (259 - level))
        def contrast(c):
            return 128 + factor * (c - 128)
        return img.point(contrast)

    def parse_files(self, file):
        if type(file) is list:
            parsed_list = []
            for image in file:
                image_contrasted = self.__contrastor(image, 30)
                parsed_list.append(pytesseract.image_to_string(image_contrasted, lang='rus+eng'))
            return parsed_list
        image_contrasted = self.__contrastor(file, 30)
        return [pytesseract.image_to_string(image_contrasted, lang='rus+eng')]

class Base_:
    def __init__(self):
        # Connect to the database
        self.connection = pymysql.connect(host=sc.host,
                                    user=sc.user,
                                    password=sc.password,
                                    db=sc.db,
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)

    def execute(self, command):
        self.connection.begin()
        result = None
        try:
            with self.connection.cursor() as cursor:
                # Read a single record
                cursor.execute(command)
                result = cursor.fetchall()
        finally:
            self.connection.close()
        return result

    def select(self, table_name):
        # SELECT FROM database
        return self.execute("SELECT * FROM `"+table_name+"`")

    def insert(self, table_name, data):
        #print("INSERT INTO `"+ table_name+"` " + str_keys + " VALUES "+ str_vals +";")
        print("INSERT INTO `"+ table_name+"` " + str(data.keys()).replace('[','').replace(']','').replace('dict_keys','').replace("'",'') + " VALUES "+ str(data.values()).replace('[','').replace(']','').replace('dict_values','').replace("'",'"') +";")

        #return self.execute("INSERT INTO `parsed` (`type`, `data`, `status`) VALUES (%s, %s, %s)", (str(data['type']), str(data['data']), data['status']))

    def select_json(self, table_name):
        data = list()
        base_data = self.select(table_name)
        for dat in base_data:
            print('load: ', dat)
            data.append(dat)
        return data

    @staticmethod
    def clean_table_messages():
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)
        result = None
        try:
            with connection.cursor() as cursor:
                # Create a new record

                cursor.execute("DELETE FROM `messages`")

            connection.commit()
        finally:
            connection.close()

        return result

    @staticmethod
    def delete_pipeline_messages(email):
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)
        result = None
        try:
            with connection.cursor() as cursor:
                # Create a new record

                cursor.execute("DELETE FROM `lastpipelines` WHERE email=%s",(email))

            connection.commit()
        finally:
            connection.close()

        return result



    def save_messages(self, table_name):
        pass

    @staticmethod
    def push_parsed(type_, data, status):
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)
        result = None
        try:
            with connection.cursor() as cursor:
                # Create a new record

                cursor.execute("INSERT INTO `parsed` (`type`, `data`, `status`) VALUES (%s, %s, %s)", (type_, data, status))

            connection.commit()
        finally:
            connection.close()

        return result

    @staticmethod
    def push_pipelines(email, speakline, progress):
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)
        result = None
        try:
            with connection.cursor() as cursor:
                # Create a new record

                cursor.execute("INSERT INTO `lastpipelines` (`email`, `speakline`, `progress`) VALUES (%s, %s, %s)", (email, speakline, progress))

            connection.commit()
        finally:
            connection.close()

        return result

    @staticmethod
    def renew_pipelines(email, speakline, progress):
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)
        result = None
        try:
            with connection.cursor() as cursor:
                # Create a new record

                cursor.execute("UPDATE lastpipelines SET speakline=%s, progress=%s WHERE email=%s;", (speakline, progress,email))

            connection.commit()
        finally:
            connection.close()
        return result

    @staticmethod
    def get_secret(acc_id):
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)
        result = None
        try:
            with connection.cursor() as cursor:
                # Create a new record

                cursor.execute("SELECT `secret` FROM `organisations` WHERE accountId=%s", (acc_id))

            connection.commit()
        finally:
            connection.close()
        return result

class Speak:
    def __init__(self, email_name, session):
        # get lock_number
        # check email name in history messages base in status active
        self.classificator = MessageClassifier()
        self.finder = KeyParser()
        self.recipients = [email_name]
        self.sender = 'megabot@cometbot.ru'
        self.session = session
        self.base = Base_()


        self.email_name = email_name
        with open("speak_lines.json", "r", encoding='utf-8') as speak_file:
            self.speak_lines = json.load(speak_file)

    def get_last_sended(self, email_name):  # get last sended index from base for user email
        # return None
        self.base = Base_()
        pipelines = self.base.select_json('lastpipelines')
        for line in pipelines:
            if line['email'] == email_name:
                return line['speakline'], line['progress']
        Base_.push_pipelines(email_name, 0,1)
        return None

    def get_resp(self, speak_line, progress, message):

        bool_is, data = self.classificator.is_bool(message)
        if bool_is:
            if data['exit_code']:
                progress = self.speak_lines[speak_line][progress]['yes']
                if len(self.speak_lines[speak_line][progress]['yes']) == 0:
                    data['remove']=True
                self.lock_index = (speak_line, progress)
                print('data 1 ', data)
                return self.speak_lines[speak_line][progress], data
            elif data['exit_code'] == False:
                if len(self.speak_lines[speak_line][progress]['not']) == 0:
                    data['remove'] = True
                else:
                    progress = self.speak_lines[speak_line][progress]['not']
                    self.lock_index = (speak_line, progress)
                print('data 1 ', data)
#                if data['number']
#                    self.lock_index = (speak_line, progress)
                return self.speak_lines[speak_line][progress], data
        else:
            if self.classificator.classify(message,True) is None:
                print('is None')
                return None
            try:
                index, data = self.classificator.classify(message,True)
                if index == (2,2):
                    if len(self.speak_lines[speak_line][progress]['not']) == 0:
                        data['remove']=True
                    else:
                        progress = self.speak_lines[speak_line][progress]['not']
                        self.lock_index = (speak_line, progress)
                    return self.speak_lines[speak_line][progress], data
                else:
                    if len(self.speak_lines[speak_line][progress]['not']) == 0:
                        data['remove']=True
                    else:
                        progress = self.speak_lines[speak_line][progress]['not']
                        self.lock_index = (speak_line, progress)
                    return self.speak_lines[speak_line][progress], data
                return None
            except:
                return None


    def send_response(self, message):
        self.lock_index = self.get_last_sended(self.email_name)
        if self.lock_index is None:
            classi_ = self.classificator.classify(message)
            if classi_ is None:
                print('Is none', 'Add message to fail base')
                Base_.push_parsed('Fail body or attach message', str(message), -1)
                return
            self.lock_index, data = classi_[0], classi_[1]
            try:
                pipeline = self.speak_lines[str(self.lock_index[0])][str(self.lock_index[1])]
            except KeyError:
                print("Error keys not found", self.lock_index)
                return None
            unkey_text = unkeyer(pipeline['text'], data)
            # save to base lock_index
            #print(unkey_text)
            send_mail(self.sender, self.recipients, unkey_text)
            print('Send ',unkey_text,'to ', self.recipients)
        else:
            response = self.get_resp(str(self.lock_index[0]),str(self.lock_index[1]), message)
            if response is None:
               Base_.delete_pipeline_messages(self.email_name)
               return
            pipeline, data = response[0], response[1]
            if data is not None:
                #print(data)
                unkey_text = unkeyer(pipeline['text'], data)
                print(unkey_text)
                send_mail(self.sender, self.recipients, unkey_text)
                print('Send ',unkey_text,'to ', self.recipients)
                if response[1].get('remove') == True:
                    Base_.delete_pipeline_messages(self.email_name)
                    type_ = data.get('type')
                    if type_ == None:
                        type_ == 'Not detecting type'
                    Base_.push_parsed(type_, str(message), 0)
                    return
            else:
                send_mail(self.sender, self.recipients, pipeline['text'])
                print('Send ',pipeline['text'],'to ', self.recipients)
            # send text to email with reply history
            Base_.renew_pipelines(self.email_name, self.lock_index[0], self.lock_index[1])




    # # get_messages
    # parsed = {}
    # messages = Base_.select_json('messages')
    # users = Base_.select_json("users")
    # for message in messages:
    #     sender = message['sender']
    #     print(message["body"])
    #     # get lk_number from text or attach
    #     # check access email and sender_email
    #     # parse
    #     # add parse data to parsed
    #     # add status to parsed
    # Base_.clean_base("messages")
    # # push parsed base


def format_key(key):
    return '%'+key+'%'

def unkeyer(str_, box):
    for key in box.keys():
            if type(box[key]) is str and str_.find(format_key(key)) > -1:
                str_ = str_.replace(format_key(key), box[key])
    return str_
#     test_str = u'Подключите услугу «Командировка» на номере\n'\
#     u'1271132111 кодовое слово: Слон и Моська'
# test_str2 = u'Подключите услугу «Роуминг Гудбай»\n'\
#     u'1271132111\n\n'\
#     u'Слон'
