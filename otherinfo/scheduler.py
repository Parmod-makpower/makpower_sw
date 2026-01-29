from apscheduler.schedulers.background import BackgroundScheduler
from otherinfo.sync import sync_sampling_sheet, sync_not_in_stock, sync_mahotsav_sheet

def start():
    scheduler = BackgroundScheduler()

    # Sampling → 4 hours
    scheduler.add_job(sync_sampling_sheet, 'interval', hours=7)

    # Not In Stock → 6 hours
    scheduler.add_job(sync_not_in_stock, 'interval', hours=6)

    # Not In Stock → 6 hours
    scheduler.add_job(sync_mahotsav_sheet, 'interval', hours=2)

    scheduler.start()
