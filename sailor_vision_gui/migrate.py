from database import init_db, Base, engine
from models import *

if __name__ == "__main__":
    if init_db():
        print("Migration successful! Tables created :")
        print(engine.table_names())
    else:
        print("Migration failure!")