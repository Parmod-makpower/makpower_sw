
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'otherinfo'

    def ready(self):
    
        # 🕒 Scheduler को भी run होने दो जैसा पहले था
        from .scheduler import start
        start()
