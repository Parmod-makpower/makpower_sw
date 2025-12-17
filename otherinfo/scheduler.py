from apscheduler.schedulers.background import BackgroundScheduler
from otherinfo.sync import sync_sampling_sheet

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_sampling_sheet, 'interval', minutes=10)

    scheduler.start()
