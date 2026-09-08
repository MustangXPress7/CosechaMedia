"""Registro centralizado de dispositivos.

Este módulo agrupa la gestión de dispositivos conocidos, nombres de cámara y
configuraciones de dispositivo que antes estaban dispersos en DatabaseManager.
Mantiene la compatibilidad con la API existente y sirve como fachada para
futuras separaciones.
"""

from __future__ import annotations

from typing import Optional, Dict, List

from app.core.db import db as _db
from app.core.db import usb_device_id


def _sanitize_dispositivo_nombre(name: str) -> str:
    return _db._sanitize_dispositivo_nombre(name)


def upsert_known_device(device_id: str, device_type: str, name: str = None,
                        serial: str = None, last_camera: str = None,
                        metadata: dict = None) -> int:
    return _db.upsert_known_device(device_id, device_type, name, serial, last_camera, metadata)


def get_known_device(device_id: str):
    return _db.get_known_device(device_id)


def list_known_devices() -> List[dict]:
    return _db.list_known_devices()


def delete_known_device(device_id: str) -> bool:
    return _db.delete_known_device(device_id)


def delete_known_devices_by_type(device_type: str) -> int:
    return _db.delete_known_devices_by_type(device_type)


def sync_device_settings_to_known() -> int:
    return _db.sync_device_settings_to_known()


def list_known_camera_names() -> List[str]:
    return _db.list_known_camera_names()


def delete_all_known_cameras() -> None:
    _db.delete_all_known_cameras()


def delete_all_saved_devices() -> None:
    _db.delete_all_saved_devices()


def save_dispositivo(volume_serial: str, nombre_dispositivo: str,
                     brand: str = None, model: str = None) -> None:
    _db.save_dispositivo(volume_serial, nombre_dispositivo, brand, model)


def get_dispositivo_for_card(volume_serial: str):
    return _db.get_dispositivo_for_card(volume_serial)


def get_dispositivo_for_device(device_id: str):
    return _db.get_dispositivo_for_device(device_id)


def save_dispositivo_config(device_id: str, nombre_dispositivo: str) -> None:
    _db.save_dispositivo_config(device_id, nombre_dispositivo)


def get_device_delicate(device_key: str):
    return _db.get_device_delicate(device_key)


def set_device_delicate(device_key: str, delicate: bool) -> None:
    _db.set_device_delicate(device_key, delicate)


def repair_duplicate_usb_keys() -> int:
    return _db.repair_duplicate_usb_keys()


__all__ = [
    "upsert_known_device",
    "get_known_device",
    "list_known_devices",
    "delete_known_device",
    "delete_known_devices_by_type",
    "sync_device_settings_to_known",
    "list_known_camera_names",
    "delete_all_known_cameras",
    "delete_all_saved_devices",
    "save_dispositivo",
    "get_dispositivo_for_card",
    "get_dispositivo_for_device",
    "save_dispositivo_config",
    "get_device_delicate",
    "set_device_delicate",
    "repair_duplicate_usb_keys",
    "usb_device_id",
    "_sanitize_dispositivo_nombre",
]
