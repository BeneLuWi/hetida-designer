from typing import Any

from multiprocessing import Manager

import pandas as pd

manager = Manager()

store = manager.dict()

for plant in ("plantA", "plantB"):
    for unit in ("picklingUnit", "millingUnit"):
        for position in ("influx", "outfeed"):
            # initialize writable attached metadata
            store[f"root.{plant}.{unit}.{position}.temp|Sensor Config"] = {
                "key": "Sensor Config",
                "value": {"mode": "prod"},
                "dataType": "any",
                "isSink": True,
            }

            store[
                f"root.{plant}.{unit}.{position}.anomaly_score|Overshooting Allowed"
            ] = {
                "key": "Overshooting Allowed",
                "value": False,
                "dataType": "boolean",
                "isSink": True,
            }

            # initialize writable timeseries
            store[f"root.{plant}.{unit}.{position}.anomaly_score"] = pd.DataFrame()

# initialize leaf metadata sinks
for plant in ("plantA", "plantB"):
    store[f"root.{plant}|Anomaly State"] = {
        "key": "Anomaly State",
        "value": False,
        "dataType": "boolean",
        "isSink": True,
    }
    store[f"root.{plant}.alerts"] = pd.DataFrame()


def get_store():
    return store


def get_value_from_store(key: str) -> Any:
    return get_store()[key]


def set_value_in_store(key: str, value: Any) -> None:
    get_store()[key] = value


def get_metadatum_from_store(atttached_to_id: str, key: str) -> dict:
    return store[atttached_to_id + "|" + key]


def set_metadatum_in_store(atttached_to_id: str, key: str, new_value: Any) -> None:
    store[atttached_to_id + "|" + key] = new_value
