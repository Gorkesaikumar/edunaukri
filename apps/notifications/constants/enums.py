from django.db import models


class NotificationChannel(models.TextChoices):
    IN_APP = "in_app", "In App"
    EMAIL = "email", "Email"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
