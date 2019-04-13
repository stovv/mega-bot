import json
import os
import re

import pymysql.cursors
import pytesseract
from pdf2image import convert_from_path

try:
    from PIL import Image
except ImportError:
    import Image

class KeyParser:
    def __init__(self):
        self.num_with_text = re.compile(r"номер[еау][\s:]+[0-9]{3,12}")
        self.num_only = re.compile(r"[0-9]{3,12}")
        self.code_with_text = re.compile(r"код.+\s+сло.+[:= -]+[а-яА-Я ]{3,20}")
        self.code_only = re.compile(r"[а-яА-Я ]{3,20}")

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

    def find_all(self, text):
        return self.find_num(text), self.find_key(text)

class TextClassifier:
    def __init__(self):
        pass
    def classify(self, text):
        return 0

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
    @staticmethod
    def select(base_name):
        # Connect to the database
        connection = pymysql.connect(host='localhost',
                                    user='a0231165_megabot_base',
                                    password='megabotiscool',
                                    db='a0231165_messages_data',
                                    charset='utf8',
                                    cursorclass=pymysql.cursors.DictCursor)

        result = None
        try:
            with connection.cursor() as cursor:
                # Read a single record
                cursor.execute("SELECT * FROM `"+base_name+"`")
                result = cursor.fetchall()
        finally:
            connection.close()
        return result

    @staticmethod
    def select_json(base_name):
        data = list()
        base_data = Base_.select(base_name)
        for dat in base_data:
            data.append(json.loads(dat))
        return data

    @staticmethod
    def clean_base(base_name):
        pass

    @staticmethod
    def add_to_base():
        pass

    @staticmethod
    def save_messages():
        pass
