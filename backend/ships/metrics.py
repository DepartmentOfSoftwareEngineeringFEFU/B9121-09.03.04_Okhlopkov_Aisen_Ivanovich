from math import floor, sqrt, radians, sin, cos, hypot
from itertools import product

COURSES = list(range(0, 360, 30))  # 12 направлений: 0°, 30°, ..., 330°
SPEEDS = [2, 4, 6, 8, 10]  # Примерные скорости в узлах
TIME_WINDOW = 600  # Время анализа — 10 минут
MIN_DISTANCE = 0.5  # Критическая дистанция сближения в километрах

def calculate_intensity(cells, ships):
    metrics = []
    for cell in cells:
        count = 0
        for ship in ships:
            latest_position = ship.positions.last()
            if not latest_position:
                continue

            if (cell.min_lat <= latest_position.latitude <= cell.max_lat and
                cell.min_lon <= latest_position.longitude <= cell.max_lon):
                count += 1
        metrics.append({
            'cell_center': cell.cell_center,
            'value': count
        })
    return metrics

def calculate_intensity_with_speed(cells, ships):
    metrics = []
    for cell in cells:
        cell_metric = 0
        for ship in ships:
            latest_position = ship.positions.last()
            if not latest_position:
                continue

            if (cell.min_lat <= latest_position.latitude <= cell.max_lat and
                cell.min_lon <= latest_position.longitude <= cell.max_lon):

                speed_m_s = latest_position.speed * 0.514444

                if speed_m_s > 0:
                    weight = floor(speed_m_s / 10) + 1
                    cell_metric += weight

        metrics.append({
            'cell_center': cell.cell_center,
            'value': cell_metric
        })
    return metrics

def calculate_stability(cells, ships):
    metrics = []
    for cell in cells:
        speeds = []
        courses = []

        for ship in ships:
            latest_position = ship.positions.last()
            if not latest_position:
                continue

            if (cell.min_lat <= latest_position.latitude <= cell.max_lat and
                cell.min_lon <= latest_position.longitude <= cell.max_lon):

                speed_m_s = latest_position.speed * 0.514444
                speeds.append(speed_m_s)
                courses.append(latest_position.course)

        if len(speeds) >= 2:
            mean_speed = sum(speeds) / len(speeds)
            mean_course = sum(courses) / len(courses)

            sigma_v = sqrt(sum((v - mean_speed) ** 2 for v in speeds) / len(speeds))
            sigma_c = sqrt(sum((c - mean_course) ** 2 for c in courses) / len(courses))
        else:
            sigma_v = None
            sigma_c = None

        metrics.append({
            'cell_center': cell.cell_center,
            'sigma_v': round(sigma_v, 2) if sigma_v is not None else None,
            'sigma_c': round(sigma_c, 2) if sigma_c is not None else None
        })

    return metrics

def compute_t_cpa(x1, y1, v1, c1, x2, y2, v2, c2):
    dx = x2 - x1
    dy = y2 - y1

    vx1 = v1 * sin(radians(c1))
    vy1 = v1 * cos(radians(c1))
    vx2 = v2 * sin(radians(c2))
    vy2 = v2 * cos(radians(c2))

    dvx = vx1 - vx2
    dvy = vy1 - vy2

    denom = dvx ** 2 + dvy ** 2
    if denom == 0:
        return float('inf'), float('inf')

    t_cpa = - (dx * dvx + dy * dvy) / denom
    x1_cpa = x1 + vx1 * t_cpa
    y1_cpa = y1 + vy1 * t_cpa
    x2_cpa = x2 + vx2 * t_cpa
    y2_cpa = y2 + vy2 * t_cpa

    d_cpa = hypot(x1_cpa - x2_cpa, y1_cpa - y2_cpa)
    return t_cpa, d_cpa

def calculate_saturation(cells, ships):
    metrics = []
    for cell in cells:
        cell_ships = []
        for ship in ships:
            latest_position = ship.positions.last()
            if not latest_position:
                continue

            if (cell.min_lat <= latest_position.latitude <= cell.max_lat and
                cell.min_lon <= latest_position.longitude <= cell.max_lon):
                cell_ships.append((ship, latest_position))

        danger_fractions = []
        for ship, ship_pos in cell_ships:
            ship_x, ship_y = ship_pos.longitude, ship_pos.latitude
            danger_count = 0
            total_combinations = len(COURSES) * len(SPEEDS)

            for course, speed in product(COURSES, SPEEDS):
                speed_km_min = speed * 1.852 / 60

                for target in ships:
                    if ship == target:
                        continue
                    target_pos = target.positions.last()
                    if not target_pos:
                        continue

                    t_x, t_y = target_pos.longitude, target_pos.latitude
                    target_speed = target_pos.speed * 1.852 / 60
                    target_course = target_pos.course

                    t_cpa, d_cpa = compute_t_cpa(
                        ship_x, ship_y, speed_km_min, course,
                        t_x, t_y, target_speed, target_course
                    )

                    if 0 <= t_cpa <= TIME_WINDOW / 60 and d_cpa < MIN_DISTANCE:
                        danger_count += 1
                        break

            danger_fraction = danger_count / total_combinations if total_combinations > 0 else 0
            danger_fractions.append(danger_fraction)

        saturation = round(sum(danger_fractions) / len(danger_fractions), 3) if danger_fractions else 0
        metrics.append({
            'cell_center': cell.cell_center,
            'value': saturation
        })

    return metrics

