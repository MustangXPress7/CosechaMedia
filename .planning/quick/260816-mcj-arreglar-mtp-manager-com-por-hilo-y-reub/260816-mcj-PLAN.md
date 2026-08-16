---
phase: 260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - app/core/mtp.py
  - app/ui/main_window.py
  - tests/test_mtp.py
  - tests/test_source_content.py
autonomous: true
requirements: [UI-04, UI-05]
estimate:
  tokens: 30000
  raw_tokens: 30000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "MTP vuelve a detectar dispositivos: el manager COM (`IPortableDeviceManager`) se crea por hilo con `threading.local()` — el staging lanzado por auto-sync en un QThread worker y el `list_devices()` del hilo principal ya no comparten objeto COM entre apartamentos (`RPC_E_WRONG_THREAD` eliminado). El nombre de dispositivo compuesto usa `f\"{self.name}_{self.serial}\"` (sin el nombre duplicado)."
    - "«Volcado selectivo…» está en la fila de orígenes (`src_scan_row`, justo después de «Escanear cámaras») y NO aparece en «Acciones post-ingesta → Operaciones»; el slot `_open_selective_dump` no cambia."
    - "La columna «Ruta de origen» es redimensionable (`QHeaderView.Interactive` con ancho por defecto 320); las columnas de borrado (ambas tablas) son fijas y estrechas (Fixed 40 px) y no se estiran."
    - "La tabla de orígenes tiene una 4ª columna de borrado a la derecha del todo que elimina el origen con la confirmación existente (default No); el botón papelera de la cabecera (`btn_remove_source`) y su lógica desaparecen."
    - "La tabla de archivos de ingesta tiene una columna de borrado a la derecha que solo quita la fila de la vista (equivalente per-fila de `_clear_completed_rows`, nunca borra sesiones ni archivos) y resuelve la fila correcta incluso con `setSortingEnabled(True)` (patrón `indexFromItem`)."
    - "`tests/test_mtp.py` y `tests/test_source_content.py` pasan en Qt offscreen (manager thread-local mockeando comtypes/ctypes, ubicación del volcado selectivo, columnas de borrado por fila, col0 Interactive) y la suite completa `python -m unittest discover -s tests -v` no regresa."
  artifacts:
    - app/core/mtp.py
    - app/ui/main_window.py
    - tests/test_mtp.py
    - tests/test_source_content.py
  key_links:
    - "_manager() ↔ `threading.local()`: `WpdBackend.list_devices()` (hilo principal, main_window.py :233, :2871 y DevicePickerDialog) y `_WpdSession._friendly_name()` (worker QThread de staging) usan cada uno su propio `IPortableDeviceManager`; ya no existe `_DEVICE_MANAGER` global."
    - "btn_selective_dump (src_scan_row) → `_open_selective_dump` → SelectiveDumpAssistant: el método y el texto/tooltip se conservan, solo cambia el layout."
    - "source_list col 3: `setCellWidget(row, 3, _build_remove_source_button(row))` → click → `_delete_source_at_row(row)` (confirmación existente con default No) → `_remove_source_path`."
    - "table col 5: `setCellWidget(row, 5, _build_remove_file_button(filename_item))` → click → `_remove_file_row(filename_item)` → `self.table.indexFromItem(row_item).row()` → `removeRow`; sin ninguna llamada a db ni a archivos."
    - "Header source_list: col0 `QHeaderView.Interactive` + `resizeSection(0, 320)`; `setMinimumSectionSize(100)` (locked fix-4) baja a 40 porque Qt 6 clampa `resizeSection` al mínimo del header (verificado empíricamente: un Fixed 40 px con min 100 se clampa a 100 px), lo que impediría las columnas de borrado estrechas del fix-3."
---

<objective>
Corregir el fallo MTP «no detecta el dispositivo» (manager COM global compartido entre apartamentos COM) y aplicar tres mejoras de UI confirmadas por el usuario: reubicar el volcado selectivo a la fila de orígenes, añadir columnas de borrado por fila en ambas tablas y hacer la columna «Ruta de origen» redimensionable.

**Purpose:** El auto-sync con sesiones guardadas lanza el staging en un QThread worker que crea `_DEVICE_MANAGER` antes de que el usuario abra «Añadir origen»; el `list_devices()` del hilo principal reutiliza ese objeto COM de otro apartamento → `RPC_E_WRONG_THREAD` → excepción tragada → lista vacía. El singleton viola el propio docstring del módulo («COM debe inicializarse en el hilo que lo usa»). Además, la quick k7i movió por error `btn_selective_dump` a «Acciones post-ingesta → Operaciones» siendo un feature de INGESTA, el borrado de orígenes vive en un botón papelera de la cabecera que el usuario considera feo, y la columna de ruta no es redimensionable.

**Output:**
- `app/core/mtp.py`: manager COM thread-local + nombre de dispositivo sin duplicado (único cambio permitido en `app/core/`).
- `app/ui/main_window.py`: volcado selectivo en `src_scan_row`, col0 Interactive (320 por defecto), columnas de borrado por fila en `source_list` y `self.table`, retirada de `btn_remove_source`/`_remove_selected_source`/`_update_remove_source_button`.
- `tests/test_mtp.py` y `tests/test_source_content.py`: tests nuevos + suite existente sin regresiones.
</objective>

<execution_context>
@C:/Users/JoanRamon/.config/opencode/gsd-core/workflows/execute-plan.md
@C:/Users/JoanRamon/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
# Fuente de decisiones
CONTEXTO LOCKED del planning_context (quick 260816-mcj): 6 decisiones cerradas por el usuario — (1) fix MTP thread-local, (2) volcado selectivo a `src_scan_row`, (3) columnas de borrado por fila en ambas tablas, (4) col0 Interactive, (5) restricciones de proyecto, (6) cobertura de tests. No reabrir.

# Código relevante (anclas verificadas contra el archivo actual)

@C:/Users/JoanRamon/Documents/CosechaMedia/app/core/mtp.py — `_manager()` :423-436 (crea y cachea `_DEVICE_MANAGER` global con `global _DEVICE_MANAGER` :429), `_DEVICE_MANAGER = None` :439; consumidores: `WpdBackend.list_devices()` :445-476 (`_manager()` :451, `CoInitialize`/`CoUninitialize` pareados :449/:472-476) y `_WpdSession._friendly_name()` :233-240 (llamado desde el worker QThread de staging); `self.devicename` :211 (`f"{self.name}_{self.name}_{self.serial}"`, sin ningún otro consumidor en el repo — grep confirma que `devicename` solo aparece en :211); docstring :7-11 ya documenta «COM debe inicializarse en el hilo que lo usa». `threading` ya importado :21.

@C:/Users/JoanRamon/Documents/CosechaMedia/app/ui/main_window.py — `_auto_sync_check` :221-257 (`mtp.WpdBackend().list_devices()` :233 en el hilo principal vía QTimer 5 s :216-219; lanza staging en QThread con `_stage_device_in_background` :254 → :3444-3447 `_StageWorker` :89-127); `btn_remove_source` :388-394 (QPushButton fijo 24×24 en la cabecera junto al QLabel «Orígenes:» :384-386); `source_list` :411-437 (`setColumnCount(3)` :412, headers :413-414, `header.setStretchLastSection(False)` :416, comentario + `setSectionResizeMode(0, QHeaderView.Stretch)` :417-419, cols 1-2 Interactive :420-421, `setMinimumSectionSize(100)` :422, `resizeSection(1,160)/resizeSection(2,110)` :423-424, `itemSelectionChanged` → `_update_remove_source_button` :433, context menu :434-436); `src_scan_row` :439-450 (btn_detect_drives :440-443, btn_scan_cameras :444-447, `addStretch()` :449); `op_row` :625-643 (btn_reorganize :627-630, btn_clear_completed :632-635, `btn_selective_dump` :637-640, `addStretch()` :642); `self.table` :652-668 (`QTableWidget(0, 5)` :652, headers :653-656, `th.setSectionResizeMode(QHeaderView.Interactive)` :658, `setStretchLastSection(True)` :659, `resizeSection(0..3)` :660-663, `setSortingEnabled(True)` :665); `closeEvent` :1066-1076 (persiste `sourceListWidths` con 3 secciones :1073-1075); `on_file_started` :1558-1602 (toggle sorting :1559-1561/:1592-1593, items cols 0-4 :1565-1590, `_file_row_map[key] = filename_item` :1598-1599); `_clear_completed_rows` :1911-1922 (patrón de quitar filas con sorting toggle; es el modelo «solo vista» de la columna de borrado); `_refresh_source_list` :2001-2038 (col 2: `setCellWidget(row, 2, _build_content_button(...))` :2034, llama `_update_remove_source_button()` :2038); `_build_content_button` :2050+ (patrón de botón por celda con tooltip/cursor/QSS); `_remove_selected_source` :2271-2276, `_update_remove_source_button` :2278-2282, `_show_source_context_menu` :2284-2292 (se conserva — complementa al botón por fila), `_delete_source_at_row` :2294-2315 (confirmación QMessageBox.question con default No :2306-2312), `_remove_source_path` :2317-2347; `_open_selective_dump` :3780-3796 (NO cambia).

@C:/Users/JoanRamon/Documents/CosechaMedia/tests/test_mtp.py — clases existentes `TestDeviceCacheDir` :139 y `TestStaging` :149 (FakeSession/FakeBackend); no hay tests de `_manager`/COM. Import `from app.core import mtp` :6.

@C:/Users/JoanRamon/Documents/CosechaMedia/tests/test_source_content.py — setUp :23-68 (MainWindow + DatabaseManager tmp + StubNotif + `mw.db`/`ingestor_module.db` reemplazados), `test_source_list_has_content_column_with_button` :70-76 (patrón `cellWidget(row, col)`), `tearDown` :63-68 (restaura singletons). Este archivo es el hogar natural de los tests de la tabla de orígenes y de la tabla de ingesta.

@C:/Users/JoanRamon/Documents/CosechaMedia/tests/test_e2e.py — patrón de instanciación de MainWindow con DB tmp.

# Restricciones verificadas
- `app/core/` NO se toca salvo `mtp.py` (decisión 5) y en `mtp.py` SOLO `_manager()`/`_DEVICE_MANAGER` y la línea 211 — sin cambios de API pública ni de la firma de `list_devices`/`stage`.
- La columna «Contenido» de `source_list` (botón `_build_content_button` → `_open_content_filter`, modo "filter") ya cubre el per-origen «seleccionar rango»: NO duplicar esa capacidad con el volcado selectivo.
- `_show_source_context_menu` («Eliminar origen…») se conserva: el usuario pidió añadir la columna, no retirar el menú contextual.
- `_open_selective_dump` y `_build_content_button` no cambian; `test_selective_dump_button_present` (test_source_content :121-125, hasattr + click) debe seguir pasando — el botón solo cambia de layout.
- Strings nuevos en ES vía `self.tr(...)` (decisión 5); sin comentarios innecesarios; sin tocar README; sin paquetes nuevos.
- Verificación empírica Qt 6 (hecha en planificación, reproduzca si dudara): `resizeSection` sobre un header con `minimumSectionSize(100)` clampa el ancho a 100 incluso con `QHeaderView.Fixed` (por eso el mínimo baja a 40, ver key_links); un botón `setFixedSize(24,24)` dentro de `setCellWidget` conserva su geometría sea cual sea el ancho de la columna; `setCellWidget` + `setSortingEnabled(True)`: el widget viaja con su fila al ordenar y `indexFromItem(item).row()` devuelve la fila actual correcta.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Manager COM por hilo (thread-local) en mtp.py + tests</name>
  <files>app/core/mtp.py, tests/test_mtp.py</files>
  <behavior>
    - Test 1 (`test_manager_is_thread_local`): con `_ensure_types` parcheado a no-op y `comtypes.client.CreateObject` mockeado (side_effect que registra cada creación), `_manager()` devuelve el MISMO objeto en dos llamadas del mismo hilo y un objeto DISTINTO (creado en ese hilo) desde otro hilo (`threading.Thread`); total de creaciones == 2.
    - Test 2 (`test_list_devices_uses_current_thread_manager`): con `mtp._manager` parcheado a un fake DM, `WpdBackend().list_devices()` devuelve los `DeviceInfo` que expone ese DM (GetDevices side-effect), sin RPC_E_WRONG_THREAD — cubre la regresión exacta (list_devices del hilo principal tras un staging en worker).
    - Test 3 (`test_wpd_session_devicename_no_duplicate`): una `_WpdSession` construida con COM mockeado (CreateObject chain + DM fake + `_pkey` parcheado) tiene `devicename == f"{pnp_id}_{serial}"` y NO `f"{pnp_id}_{pnp_id}_{serial}"`.
  </behavior>
  <action>En `app/core/mtp.py` (anclas verificadas: `_manager()` :423-436, `_DEVICE_MANAGER = None` :439, `self.devicename` :211):

  FIX MTP (decisión 1) — manager COM por hilo:
  1. Sustituir el singleton global por thread-local (el módulo ya importa `threading` :21):
     - Añadir a nivel de módulo: `_manager_local = threading.local()` (junto a `_load_lock`/`_types_loaded`, aprox. :153-154).
     - En `_manager()` (:423-436): eliminar la línea `global _DEVICE_MANAGER` (:429) y el cuerpo de cacheo global; en su lugar leer/escribir el atributo `device_manager` del thread-local: `dm = getattr(_manager_local, "device_manager", None)`; si es None, crear el `comtypes.client.CreateObject(port.PortableDeviceManager, clsctx=comtypes.CLSCTX_INPROC_SERVER, interface=port.IPortableDeviceManager)` y asignarlo a `_manager_local.device_manager`; devolver `dm`. Mantener intactos los imports locales y la llamada `_ensure_types()`.
     - Eliminar la línea `_DEVICE_MANAGER = None` (:439). No debe quedar ninguna referencia a `_DEVICE_MANAGER` en el módulo.
     - NO cambiar la firma ni el comportamiento de `WpdBackend.list_devices` (:445-476) ni de `stage` (:482-519): siguen llamando `_manager()` y `CoInitialize`/`CoUninitialize` pareados exactamente como hoy — el fix hace que cada hilo obtenga su propio manager.
  2. Fix cosmético (decisión 1, línea :211): `self.devicename = f"{self.name}_{self.serial}"` (eliminar el componente duplicado `_{self.name}`). `devicename` no tiene consumidores fuera de :211 (verificado por grep), cambio seguro.

  Tests — añadir en `tests/test_mtp.py` una clase `TestThreadLocalManager(unittest.TestCase)` decorada con `@unittest.skipUnless(sys.platform == "win32", "WPD/COM es Windows-only")` (MTP es feature Windows del proyecto; en CI Linux se salta igual que el resto de COM). `import threading`, `import sys` y `from unittest import mock` al tope del módulo (mock no está importado hoy en test_mtp.py). En `setUp` de la clase: guardar `mtp._ensure_types` y parchearlo a `lambda: None`, y **resetear el estado thread-local** con `mtp._manager_local = threading.local()` (el thread-local persiste entre tests del mismo hilo; sin reset, el manager cacheado del primer test contamina el resto). En `tearDown`: restaurar `mtp._ensure_types`.

  - Test 1 (thread-local): parchear `comtypes.client.CreateObject` con `side_effect` que crea un `mock.MagicMock()` y lo registra en una lista; parchear `sys.modules` con `mock.patch.dict` añadiendo `"comtypes.gen.PortableDeviceApiLib"` → un fake `mock.MagicMock()` (el `import ... as port` dentro de `_manager` resuelve desde `sys.modules`; `comtypes.gen` es un paquete real importable). Llamar `mtp._manager()` dos veces en el hilo principal y una vez dentro de un `threading.Thread` (recoger el resultado en un dict del test y hacer `t.join()`). Assert: `m1 is m2`, `m1 is not m2_thread`, `len(created) == 2`.
  - Test 2 (list_devices usa el manager del hilo): parchear `mtp._ensure_types` a no-op, `mtp._manager` con `return_value=fake_dm` (MagicMock con `GetDevices` side-effect que rellena el array de ids, p. ej. dos ids), `comtypes.CoInitialize` y `comtypes.CoUninitialize` a no-op. Assert: `WpdBackend().list_devices()` devuelve 2 `DeviceInfo` con los ids/nombres del fake DM y `fake_dm.GetDevices.call_count >= 1`.
  - Test 3 (devicename sin duplicado): construir `_WpdSession("PNP1")` herméticamente. Parchear: `mtp._ensure_types` a no-op; `mtp._manager` → fake DM con `GetDeviceFriendlyName` side-effect que SOLO hace `nlen.contents.value = 0` (así `_friendly_name` cae al fallback `buf.value or pnp_id` → devuelve "PNP1" sin tocar buffers); `mtp._pkey` → `lambda fmtid, pid: mock.MagicMock()` (evita `comtypes.pointer` sobre mocks); `comtypes.CoInitialize` y `comtypes.client.CoUninitialize` → no-op; `comtypes.client.CreateObject` con side-effect que distingue por el primer argumento: para `fake_types.PortableDeviceValues` devuelve un MagicMock (ci), para `fake_port.PortableDevice` devuelve `device_mock` (MagicMock con `.Content()`, `.Open(pnp_id, ci)`, y cadena `.Content().Properties().GetValues().GetStringValue()` → "SERIAL9"); `sys.modules` con `"comtypes.gen.PortableDeviceApiLib"` y `"comtypes.gen.PortableDeviceTypesLib"` → fakes con los atributos `PortableDevice`/`IPortableDevice`/`IPortableDeviceValues` y `PortableDeviceValues`/`PortableDeviceKeyCollection` (MagicMock crea los atributos al vuelo; asignarlos explícitamente por claridad). Assert: `sess.devicename == "PNP1_SERIAL9"` y `sess.devicename != "PNP1_PNP1_SERIAL9"`; `sess.close()` al final (seguro en no-Windows: `CoUninitialize` falla silenciosamente dentro del try de `close`).

  NO tocar nada más de `app/core/` (decisión 5). Sin comentarios nuevos salvo el mínimo «por qué» del thread-local (una línea). Commit RED (tests) y GREEN (mtp.py) por separado si se sigue TDD estricto; como mínimo los tests deben existir y pasar junto al fix en el commit final.</action>
  <verify>
    <automated>python -m unittest tests.test_mtp -v; python -c "import io; s=io.open(r'app/core/mtp.py',encoding='utf-8').read(); assert '_manager_local' in s and '_DEVICE_MANAGER' not in s, 'thread-local manager (no global)'; assert 'self.name}_{self.serial}' in s and 'self.name}_{self.name}' not in s, 'devicename sin duplicado'"</automated>
  </verify>
  <done>«_manager()» crea un «IPortableDeviceManager» por hilo vía «threading.local()»; no queda «_DEVICE_MANAGER» global en mtp.py; «list_devices» y «_WpdSession._friendly_name» (hilos distintos) usan managers propios sin RPC_E_WRONG_THREAD; «devicename» es «{name}_{serial}»; la clase «TestThreadLocalManager» (3 tests, skip en no-Windows) pasa en Windows y el resto de test_mtp no regresa.</done>
</task>

<task type="auto">
  <name>Task 2: Reubicar volcado selectivo a src_scan_row y hacer la columna Ruta redimensionable</name>
  <files>app/ui/main_window.py, tests/test_source_content.py</files>
  <action>En `app/ui/main_window.py` (anclas verificadas: `op_row`/`btn_selective_dump` :625-643, `src_scan_row` :439-450, header de `source_list` :415-424, `closeEvent` :1066-1076):

  1. MOVER `btn_selective_dump` (decisión 2) de `op_row` a `src_scan_row`:
     - Quitar el bloque :637-640 de `op_row` (def del botón + `op_row.addWidget(self.btn_selective_dump)`). `op_row` queda con btn_reorganize y btn_clear_completed antes de su `addStretch()` :642.
     - Insertar el MISMO bloque en `src_scan_row`, entre `src_scan_row.addWidget(self.btn_scan_cameras)` (:447) y `src_scan_row.addStretch()` (:449): `self.btn_selective_dump = QPushButton(self.tr("Volcado selectivo…"))`, tooltip `self.tr("Seleccionar por fecha qué archivos volcar de un origen")`, `self.btn_selective_dump.clicked.connect(self._open_selective_dump)`, `src_scan_row.addWidget(self.btn_selective_dump)`.
     - Conservar EXACTAMENTE el nombre `self.btn_selective_dump`, el texto y el connect (`test_source_content.py` :121-125 los usa: hasattr + click → `_open_selective_dump`). `_open_selective_dump` (:3780-3796) NO cambia. La columna «Contenido» (botón `_build_content_button`/`_open_content_filter`, modo "filter") no se toca: ya cubre el per-origen «seleccionar rango» — no duplicar.
  2. Col0 redimensionable (decisión 4):
     - En el header de `source_list`: reemplazar :419 por `header.setSectionResizeMode(0, QHeaderView.Interactive)`; añadir `header.resizeSection(0, 320)` (ancho por defecto razonable). Mantener `header.setStretchLastSection(False)` (:416) y `header.setSectionResizeMode(1, Interactive)`/`(2, Interactive)` (:420-421) y `resizeSection(1, 160)`/`(2, 110)` (:423-424). Quitar el comentario :417-418 (ya no describe el comportamiento).
     - **Conflicto documentado (no silenciar):** `header.setMinimumSectionSize(100)` (:422, locked fix-4) clampa TODOS los `resizeSection()` del header a 100 px (verificado empíricamente en Qt 6: `QHeaderView.Fixed` + `resizeSection(col, 40)` con min 100 → ancho 100, en cualquier orden de llamadas), lo que impediría las columnas de borrado estrechas del fix-3 («ancho fijo pequeño»). Resolución: bajar el mínimo global a 40 — `header.setMinimumSectionSize(40)` — protege igualmente las columnas de colapsarse (el mínimo 20 por defecto de Qt es menor) y la col0 conserva su 320 por defecto con Interactive. Si el revisor prefiere mantener 100, las columnas de borrado quedarían a 100 px: se ha elegido 40 para cumplir el fix-3 tal como lo pidió el usuario.
  3. Persistencia de anchos: en `closeEvent` (:1073-1075), `settings.setValue("sourceListWidths", [...])` pasa a guardar las 4 secciones: `[header.sectionSize(0), header.sectionSize(1), header.sectionSize(2), header.sectionSize(3)]` (hoy guarda 3 — la lista debe reflejar el nuevo número de columnas que añade Task 3; no hay lectura de `sourceListWidths` en el repo, solo escritura, así que el cambio es seguro).
  - `_update_source_list_height` (:2040-2048) no referencia el número de columnas: NO se toca.

  Tests — añadir en `tests/test_source_content.py` (clase `TestSourceContent`, patrón existente :70-76):
  - `test_selective_dump_button_in_scan_row_not_operations`: recorrer `self.window.findChildren(QHBoxLayout)` (importar `QHBoxLayout`); localizar el layout cuyo `itemAt(i).widget()` contiene `self.window.btn_scan_cameras` (src_scan_row) y el que contiene `self.window.btn_clear_completed` (op_row); assert `self.window.btn_selective_dump` está en el primero y NO en el segundo. (Los spacers devuelven None en `itemAt(i).widget()`: filtrar.)
  - `test_source_path_column_interactive_with_default_width`: `self.window._refresh_source_list()`; `header = self.window.source_list.horizontalHeader()`; assert `header.sectionResizeMode(0) == QHeaderView.Interactive` (importar `QHeaderView`), `header.stretchLastSection() is False`, `header.sectionSize(0) == 320`; probar la redimensión real: `header.resizeSection(0, 200)` → `header.sectionSize(0) == 200`.

  NO tocar `app/core/`. Strings: reutilizar los existentes del botón (no añadir nuevos).</action>
  <verify>
    <automated>python -m unittest tests.test_source_content -v; python -c "import io; s=io.open(r'app/ui/main_window.py',encoding='utf-8').read(); assert 'src_scan_row.addWidget(self.btn_selective_dump' in s and 'op_row.addWidget(self.btn_selective_dump' not in s, 'volcado selectivo en src_scan_row'; assert 'header.setSectionResizeMode(0, QHeaderView.Interactive)' in s and 'header.resizeSection(0, 320)' in s and 'header.setSectionResizeMode(0, QHeaderView.Stretch)' not in s, 'col0 Interactive 320'; assert 'header.setMinimumSectionSize(40)' in s, 'min 40'"</automated>
  </verify>
  <done>«Volcado selectivo…» está en la fila de orígenes (tras «Escanear cámaras») y no en Operaciones; col0 es Interactive con 320 por defecto y redimensionable de verdad (resizeSection aplica); el mínimo del header es 40; «sourceListWidths» persiste 4 anchos; los 2 tests nuevos y el resto de test_source_content pasan.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Columnas de borrado por fila en ambas tablas + retirada del botón papelera</name>
  <files>app/ui/main_window.py, tests/test_source_content.py</files>
  <behavior>
    - Test 1 (`test_source_list_has_per_row_delete_column`): tras `_refresh_source_list()`, `source_list.columnCount() == 4`, `cellWidget(0, 3)` es un `QPushButton` con texto "🗑", y `not hasattr(window, "btn_remove_source")`.
    - Test 2 (`test_source_delete_button_removes_source_with_confirmation`): click en el botón de la fila 0 con `QMessageBox.question` mockeado a Yes → `db.get_sessions(pid) == []` y `self.src` fuera de `_source_paths`. Con question a No → la sesión sigue existiendo.
    - Test 3 (`test_files_table_delete_button_removes_row_only`): `on_file_started(ruta)` → `table.rowCount() == 1` y `cellWidget(0, 5)` presente; click → `rowCount() == 0` y el número de sesiones en BD NO cambia (solo vista, nunca borra sesiones ni archivos).
    - Test 4 (`test_files_table_delete_follows_sorting`): con `setSortingEnabled(True)`, dos filas (BBB.mp4 y AAA.mp4); tras `sortItems(0)` (ascendente → AAA fila 0), el botón de BBB se resuelve vía `indexFromItem` y su click quita SOLO la fila de BBB (queda "AAA.mp4").
  </behavior>
  <action>En `app/ui/main_window.py` (anclas verificadas: `btn_remove_source` :388-394, `source_list` :411-437, `self.table` :652-668, `on_file_started` :1558-1602, `_refresh_source_list` :2001-2038, `_remove_selected_source` :2271-2276, `_update_remove_source_button` :2278-2282, patrón `_build_content_button` :2050+, `_clear_completed_rows` :1911-1922):

  PASO 1 — Tabla de orígenes (`source_list`): columna de borrado por fila (decisión 3a):
  1. `setColumnCount(3)` → `setColumnCount(4)` (:412) y headers (:413-414) → `[self.tr("Ruta de origen"), self.tr("Cámara"), self.tr("Contenido"), ""]` (última cabecera vacía).
  2. Header: `header.setSectionResizeMode(3, QHeaderView.Fixed)` + `header.resizeSection(3, 40)` (columna estrecha que no se estira; `setStretchLastSection(False)` ya lo garantiza).
  3. En `_refresh_source_list`, tras `setCellWidget(row, 2, self._build_content_button(row, sess))` (:2034): `self.source_list.setCellWidget(row, 3, self._build_remove_source_button(row))`.
  4. Nuevo método `_build_remove_source_button(self, row)` (junto a `_build_content_button`): `btn = QPushButton("🗑")`; `btn.setObjectName("IconButton")`; `btn.setFixedSize(24, 24)`; `btn.setToolTip(self.tr("Eliminar este origen…"))`; `btn.setCursor(Qt.PointingHandCursor)`; `btn.clicked.connect(lambda: self._delete_source_at_row(row))`; return btn. La fuente_list NO es ordenable (`setSortingEnabled` nunca se activa en ella) y `_refresh_source_list` reconstruye los botones en cada refresco: capturar `row` por clausura es correcto y consistente con `_build_content_button(row, ...)`.
  5. RETIRAR el botón papelera de la cabecera y su lógica (decisión 3a):
     - Quitar el bloque :388-394 (`self.btn_remove_source` + `src_label_row.addWidget(self.btn_remove_source)`); `src_label_row` queda solo con el QLabel y su `addStretch()`.
     - Quitar la conexión `self.source_list.itemSelectionChanged.connect(self._update_remove_source_button)` (:433).
     - Quitar la llamada `self._update_remove_source_button()` al final de `_refresh_source_list` (:2038).
     - Eliminar los métodos `_remove_selected_source` (:2271-2276) y `_update_remove_source_button` (:2278-2282) completos.
     - No debe quedar NINGUNA referencia a `btn_remove_source`, `_remove_selected_source` ni `_update_remove_source_button` en el archivo.
  6. Conservar `_show_source_context_menu` (:2284-2292) y `_delete_source_at_row` (:2294-2315, confirmación con default No) intactos — la columna reutiliza la misma confirmación.

  PASO 2 — Tabla de archivos de ingesta (`self.table`): columna de borrado que SOLO quita la fila de la vista (decisión 3b):
  1. `QTableWidget(0, 5)` → `QTableWidget(0, 6)` (:652); headers (:653-656) → añadir `""` como sexta cabecera.
  2. Header (`th`, :657-663): `th.setStretchLastSection(True)` → `th.setStretchLastSection(False)` (si no, la columna de borrado —la última— se estiraría); añadir `th.setSectionResizeMode(4, QHeaderView.Stretch)` (Destino sigue aprovechando el ancho disponible) y `th.setSectionResizeMode(5, QHeaderView.Fixed)` + `th.resizeSection(5, 40)`.
  3. En `on_file_started`, justo después de `self.table.setItem(row, 4, dest_item)` (:1588-1590) y ANTES del bloque de re-habilitación del sorting (:1592-1593): `self.table.setCellWidget(row, 5, self._build_remove_file_button(filename_item))`.
  4. Nuevos métodos (junto a `_build_content_button`):
     - `_build_remove_file_button(self, row_item)`: botón idéntico al del PASO 1 pero `setToolTip(self.tr("Quitar de la vista…"))` y conectado a `lambda: self._remove_file_row(row_item)` — se captura el ITEM (no el índice) porque la tabla es ordenable.
     - `_remove_file_row(self, row_item)`: `row = self.table.indexFromItem(row_item).row()`; `if row < 0: return` (item huérfano tras `_clear_completed_rows`/remociones previas); `self.table.removeRow(row)`. SIN ninguna llamada a db ni a archivos — equivalente per-fila de `_clear_completed_rows` (:1911-1922). La entrada del `_file_row_map` queda huérfana igual que con `_clear_completed_rows` hoy (comportamiento existente aceptado); `on_copy_progress`/`on_file_finished` ya sobreviven a items huérfanos.
  5. NO tocar `_clear_completed_rows` ni `_show_table_context_menu`.

  PASO 3 — Tests (añadir en `tests/test_source_content.py`, clase `TestSourceContent`; importar `QHeaderView`, `QPushButton` y `mw.QMessageBox`):
  - Test 1: tras `_refresh_source_list()`, asserts de `columnCount() == 4`, `cellWidget(0, 3)` (tipo QPushButton, texto "🗑") y `not hasattr(self.window, "btn_remove_source")`.
  - Test 2: `self.window._refresh_source_list()`; `btn = self.window.source_list.cellWidget(0, 3)`; con `mock.patch.object(mw.QMessageBox, "question", return_value=mw.QMessageBox.Yes)`: `btn.click()` → `self.db.get_sessions(self.pid) == []` y `self.src not in self.window._source_paths`. Segundo test con `return_value=mw.QMessageBox.No` → sigue habiendo 1 sesión.
  - Test 3: `self.window.on_file_started(os.path.join(self.src, "clip.mp4"))` → `rowCount() == 1`; `btn = self.window.table.cellWidget(0, 5)` no None; `btn.click()` → `rowCount() == 0`; `len(self.db.get_sessions(self.pid))` sin cambios.
  - Test 4: `on_file_started` para "BBB.mp4" y "AAA.mp4"; `key = self.window._file_row_key(os.path.join(self.src, "BBB.mp4"), None)`; `item = self.window._file_row_map[key]`; `self.window.table.sortItems(0)`; `row = self.window.table.indexFromItem(item).row()` (debe ser 1 con ascendente); `self.window.table.cellWidget(row, 5).click()` → `rowCount() == 1` y `self.window.table.item(0, 0).text() == "AAA.mp4"`.
  - Test 5 — ACTUALIZAR los 2 tests existentes que asumen los conteos antiguos (sin este paso la suite no regresa: el verify de Task 3 y la truth «suite completa no regresa» fallarían). Editar en `tests/test_source_content.py`:
    - `test_source_list_has_content_column_with_button` (:70-76): `assertEqual(self.window.source_list.columnCount(), 3)` (:72) → `assertEqual(self.window.source_list.columnCount(), 4)` — la 4ª columna de borrado del PASO 1. El resto del test no cambia (`cellWidget(0, 2)` sigue siendo el botón "Todo").
    - `test_ingest_table_has_progress_column` (:116-119): `assertEqual(self.window.table.columnCount(), 5)` (:117) → `assertEqual(self.window.table.columnCount(), 6)` y el bucle de cabeceras `for i in range(5)` (:118) → `for i in range(6)` — la 6ª columna de borrado del PASO 2. El assert `self.assertIn("Progreso", headers)` no cambia (el "Progreso" sigue en los headers).

  NO tocar `app/core/` (el borrado por fila de la tabla de ingesta no debe tocar db ni ingestor). Strings nuevos vía `self.tr(...)`. Commit RED (tests) y GREEN (producción) si se sigue TDD estricto.</action>
  <verify>
    <automated>python -m unittest tests.test_source_content tests.test_e2e -v; python -c "import io; s=io.open(r'app/ui/main_window.py',encoding='utf-8').read(); assert 'btn_remove_source' not in s and '_remove_selected_source' not in s and '_update_remove_source_button' not in s, 'boton papelera retirado'; assert 'setCellWidget(row, 3, self._build_remove_source_button(row))' in s and 'def _build_remove_source_button' in s, 'columna borrado source_list'; assert 'QTableWidget(0, 6)' in s and 'setCellWidget(row, 5, self._build_remove_file_button(filename_item))' in s and 'def _remove_file_row' in s and 'indexFromItem(row_item).row()' in s, 'columna borrado tabla ingesta'; assert 'th.setStretchLastSection(False)' in s and 'setSectionResizeMode(4, QHeaderView.Stretch)' in s and 'setSectionResizeMode(5, QHeaderView.Fixed)' in s, 'header tabla ingesta'; t=io.open(r'tests/test_source_content.py',encoding='utf-8').read(); assert 'source_list.columnCount(), 4' in t and 'table.columnCount(), 6' in t and 'range(6)' in t, 'tests existentes actualizados a 4/6 columnas'"</automated>
  </verify>
  <done>«source_list» tiene 4 columnas con borrado por fila (🗑 24×24, Fixed 40 px) que elimina el origen con la confirmación existente (default No); «btn_remove_source», «_remove_selected_source» y «_update_remove_source_button» no existen; «self.table» tiene 6 columnas con borrado por fila que solo quita la fila de la vista (sin tocar sesiones/archivos) y resuelve la fila correcta con la tabla ordenada; los 4 tests nuevos, los 2 tests existentes actualizados («test_source_list_has_content_column_with_button» → columnCount 4; «test_ingest_table_has_progress_column» → columnCount 6 y «range(6)») y las suites test_source_content/test_e2e pasan.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Hilo worker (staging QThread) ↔ hilo principal (UI) | Objetos COM WPD compartidos entre apartamentos COM → RPC_E_WRONG_THREAD. El fix hace el `IPortableDeviceManager` thread-local: cada hilo crea y usa el suyo. |
| UI tabla → acciones de borrado | La columna de borrado de la tabla de ingesta no debe cruzar la frontera hacia BD/disco: solo `removeRow` sobre la vista. El borrado de la tabla de orígenes sí cruza hacia `db.delete_session` pero siempre mediado por la confirmación existente con default No. |
| cellWidget (botones) → handlers | Los botones por celda capturan fila/ítem; en la tabla ordenable la fila debe resolverse en el momento del click (`indexFromItem`), nunca la capturada en construcción. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260816-mcj-01 | Tampering | `_manager()` singleton COM global | high | mitigate | Thread-local (`threading.local()`): cada hilo crea su `IPortableDeviceManager`; elimina el cross-apartment COM que causaba RPC_E_WRONG_THREAD y la lista vacía de dispositivos (pérdida de datos por no-detección). Sin cambio de API. |
| T-260816-mcj-02 | Elevation | `_remove_file_row` (columna borrado tabla ingesta) | medium | mitigate | Solo `removeRow` vía `indexFromItem(row_item).row()` con guard `row < 0`; cero llamadas a db/fs — imposible borrar sesiones o archivos desde esta columna por construcción (equivalente per-fila de `_clear_completed_rows`). |
| T-260816-mcj-03 | Tampering | `_build_remove_source_button` → `_delete_source_at_row` | medium | mitigate | Reutiliza la confirmación existente «¿Eliminar el origen ... y sus sesiones ...?» con default No (patrón D-09 del proyecto): un click accidental no borra sin confirmación explícita. |
| T-260816-mcj-04 | DoS | Botón por celda en tabla ordenable | low | mitigate | El click resuelve la fila en tiempo de ejecución (`indexFromItem`) en lugar de la fila capturada; los items huérfanos (tras `_clear_completed_rows`/`removeRow`) devuelven -1 y el handler retorna sin efecto. |
| T-260816-mcj-SC | Tampering | pip/npm/cargo installs | low | accept | No se instala ningún paquete en este plan (solo Python del repo + unittest) — sin superficie de suministro. |
</threat_model>

<verification>
1. `python -m unittest tests.test_mtp -v` — manager thread-local (3 tests nuevos en `TestThreadLocalManager`, skip en no-Windows) + staging existente sin regresiones (Task 1).
2. `python -m unittest tests.test_source_content -v` — volcado selectivo en `src_scan_row`, col0 Interactive/320 redimensionable, columnas de borrado por fila en ambas tablas, borrado con confirmación y solo-vista, sort-safe (Tasks 2 y 3).
3. `python -m unittest tests.test_e2e -v` — MainWindow arranca y la ingesta end-to-end sigue funcionando tras los cambios de layout/columnas (Task 3).
4. Gates `python -c` con asserts (definidos en cada `<verify>`): ausencia de `_DEVICE_MANAGER`/`btn_remove_source`/`_remove_selected_source`/`_update_remove_source_button`; presencia de `_manager_local`, `resizeSection(0, 320)`, `setCellWidget(row, 3, ...)`, `setCellWidget(row, 5, ...)`, `_remove_file_row` con `indexFromItem`.
5. `python -m unittest discover -s tests -v` — suite completa sin regresiones (todas las suites existentes siguen pasando en Qt offscreen).
6. Revisión visual opcional (no bloqueante): abrir la app con un dispositivo MTP conectado y confirmar que «Añadir origen…» lista los dispositivos (fix MTP), que «Volcado selectivo…» aparece en la fila de orígenes, y que las columnas de borrado y el redimensionado de ruta se comportan.
</verification>

<success_criteria>
- MTP detecta dispositivos: el manager COM es thread-local y desaparece el `RPC_E_WRONG_THREAD` entre el staging en QThread y el `list_devices()` del hilo principal; `devicename` usa `{name}_{serial}`.
- «Volcado selectivo…» está en la fila de orígenes (tras «Escanear cámaras») y fuera de Operaciones; `_open_selective_dump` intacto.
- La columna «Ruta de origen» es Interactive (320 por defecto) y redimensionable; las columnas de borrado son Fixed 40 px y no se estiran.
- La tabla de orígenes tiene borrado por fila a la derecha con la confirmación existente (default No); el botón papelera de la cabecera y su lógica han desaparecido.
- La tabla de ingesta tiene borrado por fila que solo quita la fila de la vista y funciona con la tabla ordenable; nunca toca sesiones ni archivos.
- Tests nuevos en `tests/test_mtp.py` y `tests/test_source_content.py`; suite completa `python -m unittest discover -s tests -v` en verde.
</success_criteria>

<output>
Create `.planning/quick/260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub/260816-mcj-SUMMARY.md` when done
</output>
