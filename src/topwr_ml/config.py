'''ładowanie zmiennych z .env'''
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
