from apscheduler.schedulers.background import BackgroundScheduler
from otherinfo.sync import sync_sampling_sheet, sync_not_in_stock, sync_mahotsav_sheet

def start():
    scheduler = BackgroundScheduler()

    # Sampling
    scheduler.add_job(sync_sampling_sheet, 'interval', minutes=117)

    # Not In Stock
    scheduler.add_job(sync_not_in_stock, 'interval', minutes=129)

    # Goa Trip
    scheduler.add_job(sync_mahotsav_sheet, 'interval', minutes=739)

    scheduler.start()
