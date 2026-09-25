import sys
import os
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import machine_service


def get_machine_data(machine_id: str, timestamp: str = None) -> Optional[Dict]:
    """Retrieve the current sensor record for a machine at or closest to timestamp."""
    return machine_service.get_latest_sensor_record(machine_id, timestamp)


def get_sensor_history(machine_id: str, timestamp: str = None, limit: int = 10) -> List[Dict]:
    """Retrieve chronological recent sensor records for trend calculation."""
    return machine_service.get_sensor_history(machine_id, timestamp, limit=limit)


def get_maintenance_history(machine_id: str, timestamp: str = None) -> List[Dict]:
    """Retrieve historical maintenance logs for a machine."""
    return machine_service.get_machine_maintenance_history(machine_id, timestamp)


def get_production_history(machine_id: str, timestamp: str = None, limit: int = 10) -> List[Dict]:
    """Retrieve chronological recent production logs."""
    return machine_service.get_machine_production_history(machine_id, timestamp, limit=limit)


def get_energy_history(machine_id: str, timestamp: str = None, limit: int = 10) -> List[Dict]:
    """Retrieve chronological recent energy consumption and load logs."""
    return machine_service.get_energy_history(machine_id, timestamp, limit=limit)
