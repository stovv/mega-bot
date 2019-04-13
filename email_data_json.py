import pymysql.cursors
import urllib.request
import json

class Base_:

    @staticmethod
    def get_messages():
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
                cursor.execute("SELECT * FROM `messages`")
                result = cursor.fetchall()
        finally:
            connection.close()
        return result

    @staticmethod
    def download_file(url, local_path):
        urllib.request.urlretrieve(url, local_path)
