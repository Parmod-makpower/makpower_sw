# api/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from .sync import  sheet_to_db

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sheet_to_db, 'interval', minutes=2)
    scheduler.start()
