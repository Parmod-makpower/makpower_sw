# orders/apps.py
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        # 🔄 Import signals so LivePendingStock auto-updates
        import orders.signals  # 👈 यह जोड़ दिया

        # 🕒 Scheduler को भी run होने दो जैसा पहले था
        from .scheduler import start
        start()
