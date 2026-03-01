"""
Database connection module.

Exposes database object for use throughout app.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

connection = MongoClient(MONGO_URI)

db = connection[os.getenv("MONGO_DBNAME")]
