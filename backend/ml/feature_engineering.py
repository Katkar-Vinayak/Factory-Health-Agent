import pandas as pd
import numpy as np

def create_features(df):
    """
    Create lightweight derived features.
    Features:
    - temperature_load_ratio
    - energy_per_unit
    - vibration_load_ratio
    - production_efficiency
    """
    df = df.copy()
    
    # Avoid division by zero
    epsilon = 1e-6
    
    df['temperature_load_ratio'] = df['temperature_c'] / (df['load_percent'] + epsilon)
    df['energy_per_unit'] = df['energy_consumption_kwh'] / (df['production_output_units'] + epsilon)
    df['vibration_load_ratio'] = df['vibration_mm_s'] / (df['load_percent'] + epsilon)
    df['production_efficiency'] = df['production_output_units'] / (df['energy_consumption_kwh'] + epsilon)
    
    return df

BASE_FEATURES = [
    'temperature_c',
    'vibration_mm_s',
    'pressure_bar',
    'humidity_percent',
    'energy_consumption_kwh',
    'load_percent',
    'production_output_units',
    'operating_hours',
    'ambient_temperature_c'
]

DERIVED_FEATURES = [
    'temperature_load_ratio',
    'energy_per_unit',
    'vibration_load_ratio',
    'production_efficiency'
]

ALL_FEATURES = BASE_FEATURES + DERIVED_FEATURES
