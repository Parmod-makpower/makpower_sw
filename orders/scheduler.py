from apscheduler.schedulers.background import BackgroundScheduler
from orders.tasks import auto_hold_old_orders

scheduler_started = False


def start():
    global scheduler_started

    # ✅ duplicate scheduler stop
    if scheduler_started:
        return

    scheduler = BackgroundScheduler()

    # ✅ हर 1 घंटे बाद check
    scheduler.add_job(auto_hold_old_orders, trigger='interval', hours=10)

    scheduler.start()

    scheduler_started = True
