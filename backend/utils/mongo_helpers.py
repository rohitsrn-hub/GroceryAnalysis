"""
MongoDB data helpers — type conversion and preparation utilities.
Extracted from server.py L351-361.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any


def prepare_for_mongo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert problematic types (numpy, pandas) for MongoDB storage.

    Handles:
    - np.int64/int32 -> int
    - np.float64/float32 -> float
    - NaN/None/'nan' -> None
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if pd.isna(value) or value == 'nan':
                data[key] = None
            elif isinstance(value, (np.int64, np.int32)):
                data[key] = int(value)
            elif isinstance(value, (np.float64, np.float32)):
                data[key] = float(value)
    return data
