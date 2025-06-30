from django.urls import path
from .views import ShipListView, RouteView, traffic_metrics

urlpatterns = [
    path('api/ships/', ShipListView.as_view(), name='ship-list'),
    path('api/calculate-route/', RouteView.as_view(), name='calculate-route'),
    path('api/traffic-metrics/', traffic_metrics, name='traffic-metrics'),
]