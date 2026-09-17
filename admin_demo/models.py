from django.db import models


class ClubRules(models.Model):
    club_name = models.CharField(max_length=100, unique=True)
    rules = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.club_name
