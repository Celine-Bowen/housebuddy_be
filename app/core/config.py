import os

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@db:3306/mydatabase")

settings = Settings()