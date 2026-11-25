"""Reset the database. Usage: python init_db.py [--empty]"""
import sys
from app import init_db

init_db(with_sample_data="--empty" not in sys.argv)
print("Database initialised.")
