import asyncio
import websockets
import json
from django.core.management.base import BaseCommand
from ships.models import Ship, ShipPosition
from datetime import datetime, timezone
from asgiref.sync import sync_to_async
from django.db import transaction
import websockets.exceptions


AIS_API_KEY = "88d87ffcb9ccc5d1423e1111825a87fd51e1d51f"


async def parse_ais_data():
    uri = "wss://stream.aisstream.io/v0/stream"
    subscribe_message = {
        "APIKey": AIS_API_KEY,
        "BoundingBoxes": [[[39.0, 127.0], [47.0, 136.0]]],
        "FilterMessageTypes": ["PositionReport"]
    }

    while True:
        try:
            async with websockets.connect(uri, ping_interval=30, ping_timeout=10) as websocket:
                await websocket.send(json.dumps(subscribe_message))
                print("✅ Подключено к WebSocket")

                async for message_json in websocket:
                    message = json.loads(message_json)
                    msg_type = message.get("MessageType")

                    if msg_type == "PositionReport":
                        report = message['Message']['PositionReport']
                        metadata = message.get("MetaData", {})
                        
                        mmsi = str(report.get("UserID"))
                        name = metadata.get("ShipName", "Неизвестно")
                        lat = report.get("Latitude")
                        lon = report.get("Longitude")
                        cog = report.get("Cog", 0.0)
                        heading = report.get("TrueHeading", 0.0)
                        sog = report.get("Sog", 0.0)
                        timestamp_str = metadata.get("Timestamp")

                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        except:
                            timestamp = datetime.now(timezone.utc)

                        await sync_to_async(update_ship)(
                            mmsi, name, lat, lon, cog, heading, sog, timestamp
                        )

                        print(f"[POSITION] {mmsi} — {name} — lat={lat}, lon={lon}, speed={sog}, ts={timestamp}")

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[WARNING] WebSocket закрыт: {e}. Переподключение через 5 секунд...")
            await asyncio.sleep(5)

        except Exception as e:
            print(f"[ERROR] WebSocket error: {e}. Переподключение через 5 секунд...")
            await asyncio.sleep(5)

@transaction.atomic
def update_ship(mmsi, name, lat, lon, course, heading, speed, timestamp):
    # Обновляем или создаём судно
    ship = Ship.objects.update_or_create(
        mmsi=mmsi,
        defaults={'name': name}
    )[0]

    # Добавляем позицию судна
    ShipPosition.objects.create(
        ship=ship,
        latitude=lat,
        longitude=lon,
        course=course,
        heading=heading,
        speed=speed,
        timestamp=timestamp
    )

class Command(BaseCommand):
    help = 'Start AIS WebSocket parser'

    def handle(self, *args, **kwargs):
        print("🚢 Запуск AIS парсера...")
        asyncio.run(parse_ais_data())
