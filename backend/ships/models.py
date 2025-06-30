from django.db import models

class Ship(models.Model):
    mmsi = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.mmsi})"

class ShipPosition(models.Model):
    ship = models.ForeignKey(Ship,  on_delete=models.CASCADE, related_name='positions')
    latitude = models.FloatField()  # Широта
    longitude = models.FloatField()  # Долгота
    course = models.FloatField(blank=True, null=True)  # COG
    heading = models.FloatField(blank=True, null=True)
    speed = models.FloatField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.ship.mmsi} at {self.timestamp}"