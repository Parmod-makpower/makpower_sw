# models.py
from django.db import models

class SamplingSheet(models.Model):
    party_name = models.CharField(max_length=255)
    items = models.TextField(help_text="Comma separated item codes")

    def __str__(self):
        return self.party_name
