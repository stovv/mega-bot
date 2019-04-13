import re
import json

class KeyClassificator:
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

class DocumentReader:
    pass