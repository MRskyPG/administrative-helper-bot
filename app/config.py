import os
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')
public_bot_token = os.getenv('PUBLIC_BOT_TOKEN')
postgres_password = os.getenv('POSTGRES_PASSWORD')
postgres_database = os.getenv('POSTGRES_DATABASE')
postgres_user = os.getenv('POSTGRES_USER')
