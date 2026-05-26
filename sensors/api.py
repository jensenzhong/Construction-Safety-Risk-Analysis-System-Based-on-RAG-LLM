"""
Sensor data interface.

Currently returns mock readings. To connect real sensors, replace
the body of ``read_sensors`` with one of:
  - MQTT subscription  (common on construction sites)
  - HTTP / REST call   (weather station API)
  - Serial port read   (local hardware sensor)
"""

import random
import time
from dataclasses import dataclass


@dataclass
class SensorReading:
    temp_c: float
    wind_speed: float
    humidity_pct: float
    timestamp: float
    source: str  # "mock" | "mqtt" | "http" | "serial"


def read_sensors() -> SensorReading:
    """Return the latest sensor reading (mock data for now)."""
    return SensorReading(
        temp_c=round(random.uniform(8.0, 38.0), 1),
        wind_speed=round(random.uniform(0.5, 14.0), 1),
        humidity_pct=round(random.uniform(30.0, 90.0), 1),
        timestamp=time.time(),
        source="mock",
    )
