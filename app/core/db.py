import sys
from pymongo import MongoClient
from app.core.config import settings

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(settings.MONGO_URI, maxPoolSize=10, minPoolSize=1)
            self.db = self.client[settings.DATABASE_NAME]
            print(f"MongoDB 연결 성공: {settings.DATABASE_NAME}")
        except Exception as e:
            print(f"MongoDB 연결 실패: {e}")
            sys.exit(1)

    def disconnect(self):
        self.client.close()
        print("MongoDB 연결 해제")

db_instance = MongoDB()

def get_db():
    if db_instance.db is None:
        db_instance.connect()
    return db_instance.db