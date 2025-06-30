import { useEffect, useState } from 'react';
import '../style/MapView.css';
import { Icon, divIcon } from 'leaflet';
import { MapContainer, TileLayer, useMapEvents, Marker, Popup, Polyline, Rectangle } from 'react-leaflet';
import settingsIcon from '../img/Setting.png';
import iconUrl from '../img/IconMarker.png';
import iconShipUrl from '../img/IconShip.png';
import axios from 'axios';

function MapClickHandler({ mode, onAddMarker, onAddRoutePoint }) {
    useMapEvents({

        click(e) {
            const { lat, lng } = e.latlng;
            if (mode === 'marker') {
                onAddMarker({ lat, lng });
            } else if (mode === 'route') {
                onAddRoutePoint({ lat, lng });
            }
        },
    });
    return null;
}

const getRotatedShipIcon = (heading) => {
  const style = `
    transform: rotate(${heading}deg);
    width: 38px;
    height: 38px;
    background-image: url(${iconShipUrl});
    background-size: contain;
    background-repeat: no-repeat;
  `;

  return divIcon({
    className: 'rotated-ship-icon',
    html: `<div style="${style}"></div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
};

const generateGridCells = (latStart, latEnd, lonStart, lonEnd, step) => {
    const cells = [];
    for (let lat = latStart; lat < latEnd; lat += step) {
      for (let lon = lonStart; lon < lonEnd; lon += step) {
        cells.push({
          bounds: [
            [lat, lon],
            [lat + step, lon + step]
          ],
          center: [lat + step / 2, lon + step / 2]
        });
      }
    }
    return cells;
};

export default function MapView() {
    const [markers, setMarkers] = useState([]);
    const [routePoints, setRoutePoints] = useState([]);
    const [ships, setShips] = useState([])
    const [routePath, setRoutePath] = useState([]);
    const [selectedMetrics, setSelectedMetrics] = useState([]);
    const [trafficMetrics, setTrafficMetrics] = useState([]);
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [mode, setMode] = useState('marker');
    const [info, setInfo] = useState(null);
    const [showTrafficGrid, setShowTrafficGrid] = useState(true);
    const [gridCells, setGridCells] = useState([]);

    const handleAddMarker = (point) => {
        setMarkers((prev) => [...prev, point]);
    };

    const handleAddRoutePoint = (point) => {
        if (routePoints.length < 2) {
        setRoutePoints((prev) => [...prev, point]);
        }
    };

    const customIcon = new Icon({
        iconUrl: iconUrl,
        iconSize: [38, 38],
    });

    const fetchShipData = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/ships/');
            const data = await response.json();
            setShips(data);
        } catch (err) {
            console.error('Ошибка загрузки данных:', err);
        }
    };

    const buildRoute = async () => {
        if (routePoints.length === 2) {
            try {
                const response = await axios.post('http://localhost:8000/api/calculate-route/', {
                start: [routePoints[0]?.lat, routePoints[0]?.lng], 
                end: [routePoints[1]?.lat, routePoints[1]?.lng],
                });

                setInfo({
                    distance: response.data.distance_km,
                    time: response.data.estimated_time_hours,  
                });

                if (response.data.route) {
                    const path = response.data.route.map(([lat, lng]) => ({ lat, lng }));
                    setRoutePath(path);
                }

            } catch (error) {
                console.error('Ошибка при построении маршрута:', error);
            }
        }
    };

    const fetchTrafficMetrics = async () => {
        if (selectedMetrics.length === 0) {
            setTrafficMetrics([]);
            return;
        }

        try {
            const query = selectedMetrics.map(m => `metrics=${m}`).join('&');
            const response = await fetch(`http://localhost:8000/api/traffic-metrics/?${query}`);
            const data = await response.json();

              // Объединяем метрики по cell_center
            const merged = {};

            for (const metricName of Object.keys(data)) {
                for (const cell of data[metricName]) {
                    const key = cell.cell_center.join(',');
                    if (!merged[key]) {
                        merged[key] = { cell_center: cell.cell_center };
                    }

                    for (const [k, v] of Object.entries(cell)) {
                        if (k === 'cell_center') continue;
                        const fieldName = k === 'value' ? metricName : `${metricName}_${k}`;
                        merged[key][fieldName] = v;
                    }
                }
            }

            setTrafficMetrics(Object.values(merged));

        } catch (error) {
            console.error('Ошибка загрузки метрик:', error);
        }
    };

    useEffect(() => {
        fetchShipData();
        const interval = setInterval(fetchShipData, 5000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        fetchTrafficMetrics();
    }, [selectedMetrics]);

    useEffect(() => {
        const cells = generateGridCells(42.8, 43.4, 131.6, 132.2, 0.025);
        setGridCells(cells);
    }, []);

    const clearMarkers = () => setMarkers([]);
    const clearRoute = () => {
        setRoutePoints([]);
        setInfo(null);
        setRoutePath([]);
    };

    return (
        <div className="map-wrapper">
            <MapContainer center={[43.1155, 131.8855]} zoom={13} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution="© OpenStreetMap contributors"
                />

                <MapClickHandler
                    mode={mode}
                    onAddMarker={handleAddMarker}
                    onAddRoutePoint={handleAddRoutePoint}
                />

                {routePoints.map((point, idx) => (
                    <Marker
                        key={`route-${idx}`}
                        position={[point.lat, point.lng]}
                        icon={customIcon}
                    >
                        <Popup>{idx === 0 ? 'Начало' : 'Конец'}</Popup>
                    </Marker>
                ))}

                {markers.map((point, idx) => (
                    <Marker
                        key={`marker-${idx}`}
                        position={[point.lat, point.lng]}
                        icon={customIcon}
                        eventHandlers={{
                        contextmenu: () => {
                            setMarkers(prev => prev.filter((_, i) => i !== idx));
                        },
                        }}
                    >
                        <Popup>Lat: {point.lat}, Lng: {point.lng}</Popup>
                    </Marker>
                ))}

                {ships.map((ship, idx) => {
                    const lastPosition = ship.positions?.[ship.positions.length - 1];
                    if (!lastPosition) return null;

                    return (
                        <Marker
                            key={`ship-${idx}`}
                            position={[lastPosition.latitude, lastPosition.longitude]}
                            icon={getRotatedShipIcon(lastPosition.heading || 0)}
                        >
                            <Popup>
                                <div>
                                    <strong>{ship.name || 'Неизвестное судно'}</strong><br />
                                    MMSI: {ship.mmsi}<br />
                                    speed: {lastPosition.speed}<br />
                                    lat: {lastPosition.latitude}<br />
                                    lon: {lastPosition.longitude}<br />
                                </div>
                            </Popup>
                        </Marker>
                    );
                })}

                {routePath.length > 1 && (
                    <Polyline positions={routePath.map(p => [p.lat, p.lng])} color="blue" />
                )}

                {/* Отображение сетки */}
                {showTrafficGrid && gridCells.map((cell, idx) => (
                    <Rectangle
                        key={`grid-${idx}`}
                        bounds={cell.bounds}
                        pathOptions={{ color: 'grey', weight: 1, fillOpacity: 0.1 }}
                    />
                ))}

                {/* Отображение значений метрик в центре ячеек */}
                {showTrafficGrid && Array.isArray(trafficMetrics) && trafficMetrics.map((cell, idx) => (
                    <Marker
                        key={`cell-metric-${idx}`}
                        position={cell.cell_center}
                        icon={divIcon({
                            className: 'traffic-cell-label',
                            html: `
                                <div style="font-size: 14px; background: rgba(255,255,255,0.8); padding: 2px 4px; border-radius: 4px;">
                                    ${Object.entries(cell)
                                        .filter(([key]) => key !== 'cell_center')
                                        .map(([key, value]) => `${key}: ${value?.toFixed ? value.toFixed(2) : value}`)
                                        .join('<br/>')}
                                </div>
                            `
                        })}
                    />
                ))}
            </MapContainer>

            {!isPanelOpen && (
                <div className="settings-toggle" onClick={() => setIsPanelOpen(true)}>
                    <img src={settingsIcon} alt="Открыть настройки" className="menu-icon" />
                </div>
            )}

            <div className={`settings-panel ${isPanelOpen ? 'open' : ''}`}>
                <button className="close-btn" onClick={() => setIsPanelOpen(false)}>✖</button>
                <h2>Настройки</h2>
                <div className='mode'>
                    <button
                        onClick={() => setMode('marker')}
                        className={mode === 'marker' ? 'active' : ''}
                    >
                        🧭 Маркеры
                    </button>
                    <button
                        onClick={() => setMode('route')}
                        className={mode === 'route' ? 'active' : ''}
                    >
                        📍 Маршрут
                    </button>
                </div>

                <div style={{ marginBottom: '10px' }} className="metrics-container">
                    <p style={{ fontSize: '24px', display: 'block', marginBottom: '8px' }}>Метрики</p>

                    {[
                        { id: 'intensity', label: 'Интенсивность' },
                        { id: 'intensity_speed', label: 'Интенсивность + скорость движения' },
                        { id: 'stability', label: 'Стабильность параметров движения' },
                        { id: 'saturation', label: 'Насыщенность трафика' },
                    ].map(metric => (
                        <label key={metric.id} style={{ display: 'block', marginBottom: '6px' }}>
                        <input
                            type="checkbox"
                            value={metric.id}
                            checked={selectedMetrics.includes(metric.id)}
                            onChange={(e) => {
                            if (e.target.checked) {
                                setSelectedMetrics(prev => [...prev, metric.id]);
                            } else {
                                setSelectedMetrics(prev => prev.filter(m => m !== metric.id));
                            }
                            }}
                            style={{ marginRight: '8px' }}
                        />
                        {metric.label}
                        </label>
                    ))}

                    <button
                        onClick={() => setShowTrafficGrid(!showTrafficGrid)}
                        style={{ marginBottom: '10px'}}
                    >
                        {showTrafficGrid ? 'Скрыть метрику трафика' : 'Показать метрику трафика'}
                    </button>
                </div>

                {mode === 'marker' && (
                    <button onClick={clearMarkers} className="action-button clear-button">
                        Очистить маркеры
                    </button>
                )}

                {mode === 'route' && (
                    <>
                        <button onClick={clearRoute} className="action-button clear-button">
                            Очистить маршрут
                        </button>
                        {routePoints.length === 2 && (
                            <button onClick={buildRoute} className="action-button build-button">
                                Построить маршрут
                            </button>
                        )}
                    </>
                )}

                {info && info.distance !== undefined && info.time !== undefined && (
                    <div className="info-block">
                        <strong>Длина:</strong> {info.distance.toFixed(2)} км<br />
                        <strong>Время:</strong> {info.time.toFixed(2)} ч
                    </div>
                )}

            </div>
        </div>
    );
}