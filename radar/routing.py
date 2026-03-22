from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/radar/", consumers.RadarConsumer.as_asgi()),
]
