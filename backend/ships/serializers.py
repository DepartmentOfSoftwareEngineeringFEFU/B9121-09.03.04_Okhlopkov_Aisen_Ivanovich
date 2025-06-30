from rest_framework import serializers
from .models import Ship, ShipPosition

class ShipPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipPosition
        fields = ['id', 'latitude', 'longitude', 'course', 'heading', 'speed', 'timestamp']

class ShipSerializer(serializers.ModelSerializer):
    positions = ShipPositionSerializer(many=True, read_only=True)

    class Meta:
        model = Ship
        fields = ['id', 'mmsi', 'name', 'positions']