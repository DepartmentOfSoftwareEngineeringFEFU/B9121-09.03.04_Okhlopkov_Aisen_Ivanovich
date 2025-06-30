from collections import namedtuple

GridCell = namedtuple("GridCell", ["min_lat", "max_lat", "min_lon", "max_lon", "cell_center"])

def generate_grid_cells(lat_start=42.8, lat_end=43.4, lon_start=131.6, lon_end=132.2, step=0.025):
    cells = []
    lat = lat_start
    while lat < lat_end:
        lon = lon_start
        while lon < lon_end:
            cell = GridCell(
                min_lat=lat,
                max_lat=lat + step,
                min_lon=lon,
                max_lon=lon + step,
                cell_center=((lat + lat + step) / 2, (lon + lon + step) / 2)
            )
            cells.append(cell)
            lon += step
        lat += step
    return cells