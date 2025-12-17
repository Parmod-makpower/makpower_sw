
from apscheduler.schedulers.background import BackgroundScheduler
from .sync import  sync_dispatch_orders

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_dispatch_orders, 'interval', minutes=140)
    scheduler.start()
