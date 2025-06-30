from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from geopy.distance import geodesic
from rest_framework.decorators import api_view
from shapely.geometry import Point, LineString
from django.http import JsonResponse

from .models import Ship
from .serializers import ShipSerializer
from .grid import generate_grid_cells
from .metrics import calculate_intensity, calculate_intensity_with_speed, calculate_saturation, calculate_stability

import heapq
import os
import geopandas as gpd

GRID_SIZE = 0.0008
GRID_SIZE_METRIX = 0.01

def compute_safety(u, v, sigma_v, sigma_c, p):
    terms = [
        1 / (1 + u) if u is not None else 0,
        1 / (1 + v) if v is not None else 0,
        1 / (1 + sigma_v) if sigma_v is not None else 0,
        1 / (1 + sigma_c) if sigma_c is not None else 0,
        (1 - p) if p is not None else 0,
    ]
    return sum(terms) / 5

class ShipListView(APIView):
    def get(self, request, *args, **kwargs):
        ships = Ship.objects.all()
        serializer = ShipSerializer(ships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RouteView(APIView):
    def post(self, request):
        try:
            start = request.data.get('start') 
            end = request.data.get('end')  
            if not (start and end):
                return Response({'error': 'Неверные координаты'}, status=400)

            obstacles = get_obstacle_points()
            land_union = get_land_union()

            traffic_cells = generate_grid_cells()
            ships = Ship.objects.all()
            intensity = calculate_intensity(traffic_cells, ships)
            intensity_speed = calculate_intensity_with_speed(traffic_cells, ships)
            stability = calculate_stability(traffic_cells, ships)
            saturation = calculate_saturation(traffic_cells, ships)

            safety_map = {}
            for idx, cell in enumerate(traffic_cells):
                u = intensity[idx]['value']
                v = intensity_speed[idx]['value']
                sigma_v = stability[idx].get('sigma_v')
                sigma_c = stability[idx].get('sigma_c')
                p = saturation[idx]['value']
                f = compute_safety(u, v, sigma_v, sigma_c, p)
                safety_map[tuple(cell.cell_center)] = f

            route = astar_with_obstacles(start, end, obstacles, land_union, safety_map)
            if not route:
                return Response({'error': 'Маршрут не найден'}, status=400)

            distance_km = sum(geodesic(route[i], route[i+1]).km for i in range(len(route)-1))
            speed_knots = float(request.data.get('speed_knots', 10))
            speed_kmh = speed_knots * 1.852
            time_hours = distance_km / speed_kmh

            return Response({
                'route': route,
                'distance_km': round(distance_km, 2),
                'estimated_time_hours': round(time_hours, 2)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=400)

def get_obstacle_points():
    ships = Ship.objects.all().prefetch_related('positions')
    obstacles = set()
    buffer_radius = 0.01 

    for ship in ships:
        latest_position = ship.positions.order_by('-timestamp').first()
        if not latest_position:
            continue

        lat = round(latest_position.latitude, 3)
        lng = round(latest_position.longitude, 3)

        for dlat in [-buffer_radius, 0, buffer_radius]:
            for dlng in [-buffer_radius, 0, buffer_radius]:
                ob_lat = round(lat + dlat, 3)
                ob_lng = round(lng + dlng, 3)
                obstacles.add((ob_lat, ob_lng))

    return obstacles

def get_land_union():
    geojson_path = os.path.join("data", "map.geojson")
    if not os.path.exists(geojson_path):
        return None
    try:
        gdf = gpd.read_file(geojson_path)
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        else:
            gdf = gdf.to_crs("EPSG:4326")

        land_union = gdf.geometry.unary_union.buffer(0.001)
        return land_union
    except Exception as e:
        print("Ошибка чтения geojson:", e)
        return None

def heuristic(a, b):
    return geodesic(a, b).km

def astar_with_obstacles(start, end, obstacles, land_union, safety_map):
    start = (round(start[0], 3), round(start[1], 3))
    end = (round(end[0], 3), round(end[1], 3))

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, end)}
    visited = set()

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == end:
            return reconstruct_path(came_from, current)

        visited.add(current)

        for neighbor in get_neighbors(current, land_union):
            if neighbor in obstacles:
                continue
            if neighbor in visited:
                continue

            line = LineString([(current[1], current[0]), (neighbor[1], neighbor[0])])
            if land_union and land_union.intersects(line):
                continue

            cell_center = (round(neighbor[0], 3), round(neighbor[1], 3))
            safety = safety_map.get(cell_center, 0.5)  # default moderate safety
            risk_penalty = 1 - safety

            tentative_g = g_score[current] + heuristic(current, neighbor) + risk_penalty
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None

def get_neighbors(pos, land_union):
    lat, lng = pos
    deltas = [-GRID_SIZE, 0, GRID_SIZE]
    neighbors = []

    for dx in deltas:
        for dy in deltas:
            if dx == 0 and dy == 0:
                continue
            n_lat = round(lat + dy, 3)
            n_lng = round(lng + dx, 3)
            point = Point(n_lng, n_lat)

            if land_union and land_union.contains(point):
                continue

            neighbors.append((n_lat, n_lng))

    return neighbors

def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path

@api_view(['GET'])
def traffic_metrics(request):
    metrics_param = request.GET.getlist('metrics')

    if not metrics_param:
        return Response({'error': 'Нет выбранных метрик'}, status=400)

    ships = Ship.objects.all()
    cells = generate_grid_cells()

    result = {}

    for metric_type in metrics_param:
        if metric_type == 'intensity':
            result['intensity'] = calculate_intensity(cells, ships)
        elif metric_type == 'intensity_speed':
            result['intensity_speed'] = calculate_intensity_with_speed(cells, ships)
        elif metric_type == 'stability':
            result['stability'] = calculate_stability(cells, ships)
        elif metric_type == 'saturation':
            result['saturation'] = calculate_saturation(cells, ships)
        else:
            result[metric_type] = [] 

    return Response(result)
