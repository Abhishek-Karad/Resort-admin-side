import os 
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://abhishekkarad29:vUHRQR1BneEOPoB2@cluster0.26upo.mongodb.net/KokanKinara")