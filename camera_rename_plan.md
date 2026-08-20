# Camera → Dispositivo Rename Plan

This document lists all occurrences of "camera" (case-insensitive) in `.py` files under `app/` that should be conceptually renamed to "dispositivo", along with technical terms that should be kept as-is.

## Categorization Rules

**RENAME (CONCEPTUAL)** - Terms referring to the camera as a user-facing device/organizational concept:
- "default_camera", "camera_name", "cameras" (DB table)
- DB column references: `default_camera`, `camera_name`
- UI strings referencing camera devices
- Method/variable names about camera device identity
- References to "cámara" as a concept

**KEEP (TECHNICAL)** - Terms that are technical metadata outputs or settings:
- `camera_model`, `camera_make` (ffprobe metadata outputs)
- `camera_detection_mode`, `camera_detection_timeout` (feature settings)
- `include_camera` (boolean flag for folder structure)
- `camera_first`, `camera_only` (organization type constants)
- Icon names, implementation details

---

## RENAME (CONCEPTUAL) - Sorted by file path, then line number

### app/core/db.py
| Line | Content | Category |
|------|---------|----------|
| 44 | `default_camera TEXT DEFAULT ''` | RENAME |
| 57 | `("default_camera", "TEXT DEFAULT ''")` | RENAME |
| 61 | `("camera_detection_mode", "TEXT DEFAULT 'auto'")` | KEEP |
| 62 | `("camera_detection_timeout", "INTEGER DEFAULT 5")` | KEEP |
| 77 | `include_camera INTEGER DEFAULT 1` | KEEP |
| 106 | `CREATE TABLE IF NOT EXISTS cameras` | RENAME |
| 120 | `camera_id INTEGER` | RENAME |
| 128 | `default_camera TEXT` | RENAME |
| 132 | `FOREIGN KEY (camera_id) REFERENCES cameras (id)` | RENAME |
| 146 | `("default_camera", "TEXT")` | RENAME |
| 152 | `("camera_name", "TEXT")` | RENAME |
| 189 | `camera_name TEXT` | RENAME |
| 197 | `if "camera_name" not in sd_cols:` | RENAME |
| 198 | `cursor.execute("ALTER TABLE sd_cards ADD COLUMN camera_name TEXT")` | RENAME |
| 255 | `if "camera_name" not in ds_cols:` | RENAME |
| 256 | `cursor.execute("ALTER TABLE device_settings ADD COLUMN camera_name TEXT")` | RENAME |
| 477 | `folder_name, organization_type, duration_type, default_camera` | RENAME |
| 478 | `use_metadata_date, delicate_mode, created_at, source_path, camera_name` | RENAME |
| 494 | `"default_camera": r[8]` | RENAME |
| 499 | `"camera_name": r[13]` | RENAME |
| 514 | `folder_name, organization_type, duration_type, default_camera` | RENAME |
| 515 | `use_metadata_date, delicate_mode, created_at, source_path, camera_name` | RENAME |
| 534 | `"default_camera": r[9]` | RENAME |
| 539 | `"camera_name": r[14]` | RENAME |
| 565 | `"duration_type", "default_camera", "use_metadata_date"` | RENAME |
| 567 | `"source_path", "camera_name", "content_filter"` | RENAME |
| 613 | `folder_name, organization_type, duration_type, default_camera` | RENAME |
| 614 | `use_metadata_date, delicate_mode, created_at, source_path, camera_name` | RENAME |
| 631 | `"default_camera": r[9]` | RENAME |
| 636 | `"camera_name": r[14]` | RENAME |
| 799 | `"UPDATE sessions SET source_path = ?, camera_name = ?, "` | RENAME |
| 805 | `"UPDATE sessions SET source_path = ?, camera_name = ? "` | RENAME |
| 814 | `"source_path, camera_name, device_id, device_folder, destination_override) "` | RENAME |
| 837 | `"SELECT id, name, device_folder, source_path, camera_name, "` | RENAME |
| 847 | `"camera_name": r[4]` | RENAME |
| 857 | `'''SELECT id, path, label, include_date, include_camera, order_index` | KEEP |
| 863 | `"include_date": bool(r[3]), "include_camera": bool(r[4])` | KEEP |
| 870 | `include_date: bool = True, include_camera: bool = True):` | KEEP |
| 879 | `'''INSERT INTO dump_locations (project_id, path, label, include_date, include_camera, order_index)` | KEEP |
| 889 | `allowed = {"path", "label", "include_date", "include_camera", "order_index"}` | KEEP |
| 921 | `def save_card_camera(self, volume_serial: str, camera_name: str, brand: str = None, model: str = None):` | RENAME |
| 923 | `if not volume_serial or not camera_name:` | RENAME |
| 932 | `updates = ['camera_name = ?', 'last_used = CURRENT_TIMESTAMP']` | RENAME |
| 933 | `params = [camera_name]` | RENAME |
| 946 | `'INSERT INTO sd_cards (serial, brand, model, camera_name) VALUES (?, ?, ?, ?)'` | RENAME |
| 947 | `(volume_serial, brand, model, camera_name)` | RENAME |
| 952 | `def get_camera_for_card(self, volume_serial: str):` | RENAME |
| 959 | `'SELECT camera_name FROM sd_cards WHERE serial = ?', (volume_serial,)` | RENAME |
| 963 | `if row and row['camera_name']:` | RENAME |
| 964 | `return row['camera_name']` | RENAME |
| 967 | `def get_camera_for_device(self, device_id: str):` | RENAME |
| 974 | `'SELECT camera_name FROM device_settings WHERE device_key = ?'` | RENAME |
| 979 | `if row and row['camera_name']:` | RENAME |
| 980 | `return row['camera_name']` | RENAME |
| 983 | `def save_device_camera(self, device_id: str, camera_name: str):` | RENAME |
| 985 | `if not device_id or not camera_name:` | RENAME |
| 996 | `'UPDATE device_settings SET camera_name = ? WHERE device_key = ?'` | RENAME |
| 997 | `(camera_name, device_id)` | RENAME |
| 1001 | `'INSERT INTO device_settings (device_key, camera_name) VALUES (?, ?)'` | RENAME |
| 1002 | `(device_id, camera_name)` | RENAME |

### app/core/ingestor.py
| Line | Content | Category |
|------|---------|----------|
| 78 | `def _ensure_subfolder(parent: str, camera: str, shoot_date: str,` | RENAME |
| 81 | `"""Builds subpath inside parent: {folder_name}/{camera?}/{date?}."""` | RENAME |
| 83 | `if include_camera and camera:` | KEEP |
| 84 | `parts.append(camera)` | RENAME |
| 94 | `def __init__(self, loc_id: int, path: str, include_date: bool, include_camera: bool):` | KEEP |
| 98 | `self.include_camera = include_camera` | KEEP |
| 101 | `def next_available_dir(self, camera: str, shoot_date: str,` | RENAME |
| 106 | `self.path, camera, shoot_date,` | RENAME |
| 107 | `self.include_date, self.include_camera, folder_name` | KEEP |
| 120 | `camera_rename_needed = Signal(str, str)` | RENAME |
| 126 | `order_type: str = "camera_first", duration_type: int = 1,` | KEEP |
| 127 | `default_camera: str = "",` | RENAME |
| 131 | `camera_map: Optional[Dict[str, str]] = None,` | RENAME |
| 144 | `self.default_camera = default_camera` | RENAME |
| 174 | `self._camera_mapping = {}` | RENAME |
| 175 | `self._source_camera_map = dict(camera_map) if camera_map else {}` | RENAME |
| 176 | `self._camera_lock = threading.Lock()` | KEEP |
| 341 | `known_cam = self._get_camera_for_file(source_path)` | RENAME |
| 344 | `camera_name = known_cam` | RENAME |
| 346 | `camera_name = metadata.get("camera_model", "Unknown_Camera")` | KEEP |
| 347 | `camera_name = self._sanitize_camera_name(camera_name)` | KEEP |
| 349 | `if camera_name == "Unknown_Camera" and self.default_camera:` | RENAME |
| 350 | `if camera_name == "Unknown_Camera":` | RENAME |
| 352 | `if camera_name == "Unknown_Camera":` | RENAME |
| 353 | `self.camera_rename_needed.emit(source_path, camera_name)` | RENAME |
| 355 | `self._update_camera_mapping(source_path, camera_name)` | RENAME |
| 359 | `actual_camera = self._get_camera_for_file(source_path)` | RENAME |
| 367 | `actual_camera, shoot_date, file_size` | RENAME |
| 430 | `def _pick_dump_target(self, camera: str, shoot_date: str,` | RENAME |
| 436 | `camera, shoot_date, self.order_type,` | RENAME |
| 450 | `camera, shoot_date, self.folder_name, file_size` | RENAME |
| 467 | `def _sanitize_camera_name(self, name: str) -> str:` | RENAME |
| 487 | `def _update_camera_mapping(self, file_path: str, camera_name: str):` | RENAME |
| 488 | `with self._camera_lock:` | KEEP |
| 489 | `if file_path not in self._camera_mapping:` | RENAME |
| 490 | `self._camera_mapping[file_path] = camera_name` | RENAME |
| 492 | `def _get_camera_for_file(self, file_path: str) -> str:` | RENAME |
| 493 | `with self._camera_lock:` | KEEP |
| 494 | `cam = self._camera_mapping.get(file_path)` | RENAME |
| 498 | `for src_root, cam_name in self._source_camera_map.items():` | RENAME |
| 517 | `camera_batches = {}` | RENAME |
| 520 | `camera = metadata.get("camera_model", "Unknown_Camera")` | KEEP |
| 521 | `camera = self._sanitize_camera_name(camera)` | KEEP |
| 523 | `if camera not in camera_batches:` | KEEP |
| 524 | `camera_batches[camera].append((file_path, metadata))` | KEEP |
| 525 | `camera_batches[camera].append((file_path, metadata))` | KEEP |
| 527 | `for camera_name, files in camera_batches.items():` | RENAME |
| 528 | `if camera_name == "Unknown_Camera":` | RENAME |
| 535 | `camera_name,` | RENAME |
| 537 | `"camera_first",` | KEEP |
| 557 | `def rename_camera(self, old_name: str, new_name: str):` | RENAME |
| 558 | `new_name = self._sanitize_camera_name(new_name)` | RENAME |
| 579 | `with self._camera_lock:` | KEEP |
| 580 | `for fp, cam in self._camera_mapping.items:` | RENAME |
| 582 | `self._camera_mapping[fp] = new_name` | RENAME |
| 611 | `'Cámara', session.get('camera_name', '')]` | RENAME |

### app/core/metadata_engine.py
| Line | Content | Category |
|------|---------|----------|
| 76 | `def _apply_camera_tags(self, metadata: dict, tags: dict):` | KEEP |
| 85 | `metadata["camera_model"] = model` | KEEP |
| 87 | `metadata["camera_make"] = make` | KEEP |
| 88 | `if metadata["camera_model"] in ("Unknown", "", None) and make:` | KEEP |
| 89 | `metadata["camera_model"] = make` | KEEP |
| 172 | `"camera_model": "Unknown",` | KEEP |
| 173 | `"camera_make": "Unknown",` | KEEP |
| 200 | `self._apply_camera_tags(metadata, format_tags)` | KEEP |
| 219 | `self._apply_camera_tags(metadata, tags)` | KEEP |
| 236 | `camera_from_ext = self._camera_from_extension(ext)` | KEEP |
| 237 | `if metadata["camera_model"] == "Unknown" and camera_from_ext:` | KEEP |
| 238 | `metadata["camera_model"] = camera_from_ext` | KEEP |
| 251 | `metadata = {"camera_model": "Unknown_Camera", "camera_make": "Unknown", "serial": None,` | KEEP |
| 264 | `metadata = {"camera_model": "Unknown_Camera", "camera_make": "Unknown", "serial": None,` | KEEP |
| 276 | `def _camera_from_extension(self, ext: str) -> str:` | KEEP |
| 290 | `def detect_camera_batch(self, file_paths: List[str]) -> Dict:` | KEEP |
| 291 | `camera_counts = {}` | KEEP |
| 296 | `camera = metadata.get("camera_model", "Unknown")` | KEEP |
| 297 | `if camera != "Unknown":` | KEEP |
| 298 | `camera_counts[camera] = camera_counts.get(camera, 0) + 1` | KEEP |
| 300 | `if camera_counts:` | KEEP |
| 301 | `dominant_camera = max(camera_counts.items(), key=lambda x: x[1])` | KEEP |
| 303 | `"primary_camera": dominant_camera[0],` | KEEP |
| 304 | `"camera_counts": camera_counts,` | KEEP |
| 305 | `"confidence": dominant_camera[1] / min(len(file_paths), 10)` | KEEP |
| 309 | `"primary_camera": "Unknown",` | KEEP |
| 310 | `"camera_counts": {},` | KEEP |

### app/core/sd_reader.py
| Line | Content | Category |
|------|---------|----------|
| 156 | `if not info["brand"] and meta.get("camera_make"):` | KEEP |
| 157 | `make = str(meta["camera_make"]).upper()` | KEEP |
| 163 | `if not info["model"] and meta.get("camera_model"):` | KEEP |
| 164 | `model = str(meta["camera_model"]).strip()` | KEEP |

### app/core/utils.py
| Line | Content | Category |
|------|---------|----------|
| 15 | `def create_folder_structure(project_root: str, camera_name: str, shoot_date: str,` | RENAME |
| 16 | `order_type: str = "camera_first", folder_name: str = "Footage":` | KEEP |
| 19 | `if order_type == "camera_first":` | KEEP |
| 21 | `path = os.path.join(base_path, camera_name, shoot_date)` | RENAME |
| 23 | `path = os.path.join(base_path, camera_name)` | RENAME |
| 26 | `path = os.path.join(base_path, shoot_date, camera_name)` | RENAME |
| 28 | `path = os.path.join(base_path, camera_name)` | RENAME |
| 29 | `elif order_type == "camera_only":` | KEEP |
| 30 | `path = os.path.join(base_path, camera_name)` | RENAME |
| 35 | `path = os.path.join(base_path, camera_name, shoot_date)` | RENAME |
| 37 | `path = os.path.join(base_path, camera_name)` | RENAME |

### app/ui/main_window.py
| Line | Content | Category |
|------|---------|----------|
| 41 | `0: "camera_first",` | KEEP |
| 43 | `2: "camera_only",` | KEEP |
| 166 | `self.project_default_camera = ""` | RENAME |
| 178 | `self.project_camera_detection_mode = "auto"` | KEEP |
| 179 | `self.project_camera_detection_timeout = 5` | KEEP |
| 184 | `self._unknown_cameras = set()` | RENAME |
| 205 | `stored_mode = settings.value("camera_detection_mode", "manual")` | KEEP |
| 206 | `self.project_camera_detection_mode = stored_mode if stored_mode in ("manual", "auto") else "manual"` | KEEP |
| 207 | `self.project_camera_detection_timeout = settings.value("camera_detection_timeout", 5, type=int)` | KEEP |
| 476 | `self.btn_scan_cameras = QPushButton(self.tr("Escanear cámaras"))` | RENAME |
| 477 | `self.btn_scan_cameras.setToolTip(self.tr("Escanear cámaras de todos los orígenes checkeados"))` | RENAME |
| 478 | `icons.apply(self.btn_scan_cameras, "camera", size=14)` | KEEP |
| 479 | `self.btn_scan_cameras.clicked.connect(self._scan_all_cameras)` | RENAME |
| 867 | `def _show_camera_detection_dialog(self):` | RENAME |
| 880 | `mode_combo.setCurrentIndex(0 if self.project_camera_detection_mode != "auto" else 1)` | KEEP |
| 891 | `timeout_spin.setValue(self.project_camera_detection_timeout)` | KEEP |
| 910 | `settings.setValue("camera_detection_mode", selected)` | KEEP |
| 911 | `settings.setValue("camera_detection_timeout", timeout_spin.value())` | KEEP |
| 912 | `self.project_camera_detection_mode = selected` | KEEP |
| 913 | `self.project_camera_detection_timeout = timeout_spin.value()` | KEEP |
| 1080 | `if loc["include_camera"]:` | KEEP |
| 1211 | `'SELECT name, root_path, description, organization_type, duration_type, default_camera,'` | RENAME |
| 1228 | `self.project_default_camera = res["default_camera"] or ""` | RENAME |
| 1319 | `is_auto = self.project_camera_detection_mode == "auto"` | KEEP |
| 1321 | `self.btn_scan_cameras.setEnabled(is_auto)` | RENAME |
| 1421 | `'default_camera, folder_name, delicate_mode, use_metadata_date '` | RENAME |
| 1443 | `'default_camera, folder_name, delicate_mode, use_metadata_date) '` | RENAME |
| 1448 | `src["default_camera"], src["folder_name"],` | RENAME |
| 1454 | `'INSERT INTO sessions (project_id, name, shoot_date, status, source_path, camera_name, '` | RENAME |
| 1456 | `'SELECT ?, name, shoot_date, status, source_path, camera_name, '` | RENAME |
| 1487 | `"default_camera": None,` | RENAME |
| 1521 | `self._unknown_cameras = set()` | RENAME |
| 1526 | `camera_map = {}` | RENAME |
| 1529 | `cn = s.get("camera_name")` | RENAME |
| 1531 | `camera_map[os.path.normpath(sp)] = cn` | RENAME |
| 1532 | `self._current_camera_map = camera_map` | RENAME |
| 1539 | `DumpTarget(loc["id"], loc["path"], loc["include_date"], loc["include_camera"])` | KEEP |
| 1549 | `s_cam = sess.get("default_camera")` | RENAME |
| 1550 | `s_cam = self.project_default_camera if s_cam is None else s_cam` | RENAME |
| 1572 | `order_val = ORG_TYPE_MAP.get(s_org, "camera_first")` | KEEP |
| 1584 | `default_camera=s_cam,` | RENAME |
| 1587 | `camera_map=camera_map,` | RENAME |
| 1605 | `ing.camera_rename_needed.connect(self._on_camera_rename_needed)` | RENAME |
| 1657 | `cam_name = self._camera_for_path(source_path)` | RENAME |
| 1660 | `elif self.project_camera_detection_mode == "manual":` | KEEP |
| 1664 | `camera_item = QTableWidgetItem(cam_text)` | RENAME |
| 1665 | `camera_item.setFlags(camera_item.flags() & ~Qt.ItemIsEditable)` | RENAME |
| 1713 | `if self.project_camera_detection_mode != "manual" and metadata and metadata.get("camera_model") != "Unknown":` | KEEP |
| 1714 | `camera_item = QTableWidgetItem(metadata["camera_model"])` | KEEP |
| 1715 | `self.table.setItem(row, 1, camera_item)` | KEEP |
| 1990 | `def _on_camera_rename_needed(self, source_path, camera_name):` | RENAME |
| 1991 | `if self.project_camera_detection_mode == "manual":` | KEEP |
| 1993 | `self._unknown_cameras.add(camera_name)` | RENAME |
| 2015 | `if self.project_camera_detection_mode == "manual":` | KEEP |
| 2016 | `self._unknown_cameras.clear()` | RENAME |
| 2018 | `if not self._unknown_cameras:` | RENAME |
| 2020 | `unknown_list = list(self._unknown_cameras)` | RENAME |
| 2021 | `self._unknown_cameras.clear()` | RENAME |
| 2023 | `new_name, ok = QInputDialog.getText(` | RENAME |
| 2024 | `self.tr("Se detectó '%1' sin identificar.\nIntroduce un nombre para el dispositivo:").arg(old_name),` | RENAME |
| 2031 | `ing.rename_camera(old_name, new_cam)` | RENAME |
| 2033 | `cam_item = self.table.item(r, 1)` | RENAME |
| 2034 | `if cam_item and cam_item.text() == old_name:` | RENAME |
| 2035 | `cam_item.setText(new_cam)` | RENAME |
| 2038 | `if s.get("camera_name") == old_name:` | RENAME |
| 2039 | `sp = s.get("source_path", "")` | KEEP |
| 2040 | `self._persist_camera_mapping(s["id"], sp, new_cam)` | RENAME |
| 2047 | `# Column 1: camera name` | RENAME |
| 2038 (duplicate reference) | `if s.get("camera_name") == old_name:` | RENAME |
| 2048 | `cam = sess.get("camera_name") if sess else None` | RENAME |
| 2049 | `cam_text = cam if cam else (self.tr("Sin nombre") if self.project_camera_detection_mode == "manual" else "—")` | RENAME |
| 2074 | `def _prompt_rename_camera(self, row):` | RENAME |
| 2084 | `current = session.get("camera_name") or ""` | RENAME |
| 2085-2091 | `_prompt_rename_camera` method | RENAME |
| 2091 | `db.update_session_config(session["id"], camera_name=name.strip() or None)` | RENAME |
| 2116 | `# Column 1: camera name` | RENAME |
| 2117 | `cam = sess.get("camera_name") if sess else None` | RENAME |
| 2118 | `cam_text = cam if cam else (self.tr("Sin nombre") if self.project_camera_detection_mode == "manual" else "—")` | RENAME |
| 2120 | `if self.project_camera_detection_mode != "manual":` | KEEP |
| 2186 | `self._detect_camera_for_session(sid, path)` | RENAME |
| 2214 | `sender_name = (session.get("camera_name")` | RENAME |
| 2377 | `def _set_camera_cell_text(self, source_path, text):` | RENAME |
| 2387 | `def _camera_for_path(self, source_path):` | RENAME |
| 2388 | `camera_map = getattr(self, "_current_camera_map", None)` | RENAME |
| 2389 | `if not camera_map:` | RENAME |
| 2392 | `for root, cam in camera_map.items:` | RENAME |
| 2397 | `def _detect_camera_for_session(self, session_id, source_path):` | RENAME |
| 2408 | `known_cam = db.get_camera_for_device(device_id)` | RENAME |
| 2410 | `known_cam = db.get_camera_for_device(device_id)` | RENAME |
| 2414 | `known_cam = db.get_camera_for_card(serial)` | RENAME |
| 2418 | `db.update_session_config(session_id, camera_name=known_cam)` | RENAME |
| 2419 | `self._set_camera_cell_text(source_path, known_cam)` | RENAME |
| 2427 | `if self.project_camera_detection_mode == "manual":` | KEEP |
| 2428 | `self._set_camera_cell_text(source_path, self.tr("Sin nombre"))` | RENAME |
| 2431 | `self._set_camera_cell_text(source_path, "🔄 Escaneando…")` | RENAME |
| 2445 | `self._set_camera_cell_text(source_path, cam)` | RENAME |
| 2446 | `db.update_session_config(session_id, camera_name=cam)` | RENAME |
| 2447 | `self._persist_camera_mapping(session_id, source_path, cam)` | RENAME |
| 2448 | `self._refresh_source_list()` | KEEP |
| 2449 | `self._refresh_sessions_combo()` | KEEP |
| 2450 | `self.ingest_status_label.setText(self.tr("Cámara detectada: %1").arg(cam))` | RENAME |
| 2454 | `self._prompt_camera_name(session_id, source_path, c)` | RENAME |
| 2484 | `def _prompt_camera_name(self, session_id, source_path, suggested_name="":` | RENAME |
| 2489-2493 | `_prompt_camera_name` prompt dialog | RENAME |
| 2494 | `if ok and name.strip():` | RENAME |
| 2495 | `cam = name.strip()` | RENAME |
| 2496 | `db.update_session_config(session_id, camera_name=cam)` | RENAME |
| 2497 | `self._set_camera_cell_text(source_path, cam)` | RENAME |
| 2498 | `self._persist_camera_mapping(session_id, source_path, cam)` | RENAME |
| 2499 | `else:` | KEEP |
| 2500 | `db.update_session_config(session_id, camera_name=None)` | RENAME |
| 2501 | `self._set_camera_cell_text(source_path, self.tr("Sin nombre"))` | RENAME |
| 2502 | `self._refresh_source_list()` | KEEP |
| 2503 | `self._refresh_sessions_combo()` | KEEP |
| 2504-2506 | `self.ingest_status_label.setText(self.tr("Cámara: %1").arg(cam if ok and name.strip() else self.tr("Sin nombre")))` | RENAME |
| 2543 | `def _on_camera_cell_edited(self, item):` | RENAME |
| 2552 | `new_name = item.text().strip()` | RENAME |
| 2553 | `db.update_session_config(session["id"], camera_name=new_name or None)` | RENAME |
| 2554 | `self._refresh_sessions_combo()` | KEEP |
| 2555 | `self.ingest_status_label.setText(self.tr("Cámara: %1").arg(new_name or self.tr("Sin nombre")))` | RENAME |
| 2859 | `act_cam_detect = QAction(self.tr("Configurar detección de &cámara…"), self)` | RENAME |

### app/ui/selective_dump.py
| Line | Content | Category |
|------|---------|----------|
| 28 | `return {"camera_model": "iPhone 15", "camera_make": "Apple"` | KEEP |
| 82 | `"organization_type": 0,  # camera_first` | KEEP |
| 83 | `"default_camera": ""` | RENAME |
| 127 | `self.assertEqual(job["camera"], "iPhone 15")` | RENAME |
| 258 | `"organization_type": 0, "default_camera": ""` | RENAME |

---

## KEEP (TECHNICAL) - Summary

The following terms should remain as "camera" because they are technical metadata outputs or settings:

- **`camera_model`**: ffprobe metadata output (camera model identifier)
- **`camera_make`**: ffprobe metadata output (camera manufacturer)
- **`camera_detection_mode`**: Feature setting (manual/auto detection mode)
- **`camera_detection_timeout`**: Feature setting (seconds for auto-detection)
- **`include_camera`**: Boolean flag controlling whether camera name appears in folder path
- **`camera_first`**, **`camera_only`**: Organization type constants (file ordering)
- **Icon name `"camera"`**: Resource identifier for UI icons
- **`camera_id`** as just a column prefix (though references `cameras` table, the ID pattern itself is technical)

Note: While `camera_model` and `camera_make` contain "camera" in their names, they are explicit ffprobe metadata outputs that should not be renamed per the project constraints. All other occurrences that refer to the camera *device/concept* should be renamed to "dispositivo".