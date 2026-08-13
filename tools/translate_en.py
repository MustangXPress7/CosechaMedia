# -*- coding: utf-8 -*-
"""Rellena las traducciones al inglés en app/i18n/cosechamedia_en.ts.

Uso: python tools/translate_en.py
"""
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TS_PATH = os.path.join(ROOT, "app", "i18n", "cosechamedia_en.ts")

TRANSLATIONS = {
    "Ingesta Completada": "Ingest Complete",
    "Ingesta con errores": "Ingest with errors",
    "Proyecto:": "Project:",
    "Actualizar proyectos": "Refresh projects",
    "Nuevo proyecto": "New project",
    "Eliminar proyecto": "Delete project",
    "Renombrar proyecto": "Rename project",
    "Duplicar proyecto": "Duplicate project",
    "Cambiar ruta maestra del proyecto": "Change project master path",
    "Configuración": "Settings",
    "Listo": "Ready",
    "Orígenes:": "Sources:",
    "E:\\DCIM...": "E:\\DCIM...",
    "Examinar": "Browse",
    "Seleccionar origen": "Select source",
    "Elige un origen guardado para la sesión o explora una carpeta:": "Choose a saved source for the session or browse a folder:",
    "Carpetas guardadas": "Saved folders",
    "Remitentes WiFi": "WiFi senders",
    "Dispositivos FTP guardados": "Saved FTP devices",
    "(vacío)": "(empty)",
    "(ya asignado)": "(already assigned)",
    "Origen gestionado": "Managed source",
    "Ese origen ya está asignado a la sesión #%1.": "That source is already assigned to session #%1.",
    "No puedes usar una caché gestionada como origen manual.": "You cannot use a managed cache as a manual source.",
    "Origen compartido": "Shared source",
    "El remitente '%1' ya está asignado a la sesión #%2.\nSe añadirá también a la sesión #%3.": "Sender '%1' is already assigned to session #%2.\nIt will also be added to session #%3.",
    "Origen WiFi asignado a la sesión #%1": "WiFi source assigned to session #%1",
    "Ruta de origen": "Source path",
    "No hay un origen configurado para el proyecto.": "No source is configured for the project.",
    "No hay ruta maestra configurada para el proyecto.": "No master path is configured for the project.",
    "Progreso": "Progress",
    "Cámara": "Camera",
    "⟳ Detectar": "⟳ Detect",
    "Detectar unidades extraíbles": "Detect removable drives",
    "Modo guiado": "Guided mode",
    "Asistente guiado para volcados rápidos (próximamente)": "Guided assistant for quick dumps (coming soon)",
    "📷 Escanear cámaras": "📷 Scan cameras",
    "Escanear cámaras de todos los orígenes checkeados": "Scan cameras from all checked sources",
    "Sesiones:": "Sessions:",
    "Nueva sesión": "New session",
    "Eliminar sesión": "Delete session",
    "Examinar origen de sesión…": "Browse session source…",
    "Destino:": "Destination:",
    "Por defecto": "Default",
    "Personalizado": "Custom",
    "Ruta...": "Path...",
    "Examinar...": "Browse...",
    "Modo delicado": "Delicate mode",
    "INICIAR INGESTA": "START INGEST",
    "DETENER": "STOP",
    "%v / %m archivos": "%v / %m files",
    "Generar proxies": "Generate proxies",
    "Genera proxies de los clips de video tras la ingesta": "Generate proxies of video clips after ingest",
    "0 procesados": "0 processed",
    "0 pendientes": "0 pending",
    "0 errores": "0 errors",
    "Reorganizar por metadatos": "Reorganize by metadata",
    "Reorganiza los archivos en 'Unknown_Camera' detectando su cámara por metadatos": "Reorganize files in 'Unknown_Camera' by detecting their camera via metadata",
    "Formatear orígenes al acabar:": "Format sources when done:",
    "Formatea las unidades de origen al acabar el volcado y la comprobación": "Format source drives after the dump and verification",
    "Rápido": "Quick",
    "Completo": "Full",
    "Apagar al acabar": "Shut down when done",
    "Apaga el ordenador al finalizar todas las tareas de ingesta": "Shut down the computer after all ingest tasks finish",
    "Archivo": "File",
    "Estado": "Status",
    "Destino": "Destination",
    "Carpeta footage:": "Footage folder:",
    "Cámara primero": "Camera first",
    "Fecha primero": "Date first",
    "Solo cámara": "Camera only",
    "Sin subcarpetas": "No subfolders",
    "Organización:": "Organization:",
    "Un solo día": "Single day",
    "Múltiples días": "Multiple days",
    "Sin fecha": "No date",
    "Duración:": "Duration:",
    "Usar fecha de metadatos:": "Use metadata date:",
    "Fecha:": "Date:",
    "Cambiar...": "Change...",
    "(sin definir)": "(not set)",
    "Ruta maestra:": "Master path:",
    "Seleccionar ruta maestra": "Select master path",
    "Guardar": "Save",
    "Establecer como predeterminado": "Set as default",
    "Valores guardados como predeterminados.": "Values saved as defaults.",
    "Cancelar": "Cancel",
    "Detección de cámara": "Camera detection",
    "Modo": "Mode",
    "Manual": "Manual",
    "Automático (próximamente)": "Automatic (coming soon)",
    "El modo automático estará disponible próximamente.": "Automatic mode will be available soon.",
    "Tiempo máximo de escaneo": "Maximum scan time",
    "Solo aplica al modo automático, disponible próximamente.": "Only applies to automatic mode, available soon.",
    "Detección de cámara actualizada.": "Camera detection updated.",
    "Puedes añadir, duplicar, renombrar o eliminar nombres.": "You can add, duplicate, rename or delete names.",
    "Puedes añadir, renombrar o eliminar nombres.": "You can add, rename or delete names.",
    "Buscar...": "Search...",
    "Añadir": "Add",
    "Nuevo nombre:": "New name:",
    "Renombrar": "Rename",
    "Eliminar": "Delete",
    "¿Eliminar '%1'?": "Delete '%1'?",
    "Añadir...": "Add...",
    "Renombrar...": "Rename...",
    "Duplicar": "Duplicate",
    "Cerrar": "Close",
    "Personalizar carpeta de footage": "Customize footage folder",
    "Personalizar contenedores de archivos": "Customize file containers",
    "Sin proyecto": "No project",
    "Selecciona un proyecto primero.": "Select a project first.",
    "Destinos de volcado": "Dump destinations",
    "Los archivos se repartirán entre estos destinos por orden. Cuando uno esté lleno se pasará al siguiente. Deja vacío para usar la ruta maestra del proyecto.": "Files will be split among these destinations in order. When one is full, it moves to the next. Leave empty to use the project master path.",
    "fecha": "date",
    "cámara": "camera",
    "Subir": "Move up",
    "Bajar": "Move down",
    "Seleccionar destino de volcado": "Select dump destination",
    "Destino de volcado": "Dump destination",
    "Etiqueta (opcional):": "Label (optional):",
    "-- Selecciona un proyecto --": "-- Select a project --",
    "Error": "Error",
    "No se pudieron cargar los proyectos: %1": "Could not load projects: %1",
    "Aviso": "Warning",
    "Proyecto #%1 no encontrado.": "Project #%1 not found.",
    "(sin ruta)": "(no path)",
    "Proyecto: %1": "Project: %1",
    "Nombre del proyecto:": "Project name:",
    "Descripción (opcional):": "Description (optional):",
    "Proyecto #%1 creado con sesión inicial.": "Project #%1 created with initial session.",
    "No se pudo crear el proyecto: %1": "Could not create the project: %1",
    "Nuevo nombre del proyecto:": "New project name:",
    "Proyecto renombrado a '%1'.": "Project renamed to '%1'.",
    "No se pudo renombrar el proyecto: %1": "Could not rename the project: %1",
    "Nombre del proyecto duplicado:": "Name of the duplicated project:",
    "Proyecto duplicado como '%1' (ID %2).": "Project duplicated as '%1' (ID %2).",
    "No se pudo duplicar el proyecto: %1": "Could not duplicate the project: %1",
    "Sin orígenes": "No sources",
    "No hay sesiones con rutas de origen válidas.": "There are no sessions with valid source paths.",
    "Ya en marcha": "Already running",
    "El monitoreo de la SD ya está activo.": "SD monitoring is already active.",
    "Procesando...": "Processing...",
    "Procesando %1 ruta(s): %2": "Processing %1 path(s): %2",
    "En progreso": "In progress",
    "Iniciar Ingesta": "Start Ingest",
    "Ingesta detenida por el usuario": "Ingest stopped by user",
    "Detenido": "Stopped",
    "Sin nombre": "No name",
    "Detectando...": "Detecting...",
    "Copiando...": "Copying...",
    "Procesando: %1": "Processing: %1",
    "Completado": "Completed",
    "%1 procesados": "%1 processed",
    "%1 pendientes": "%1 pending",
    "Ingesta completada: %1 procesados, %2 errores, %3 omitidos.": "Ingest complete: %1 processed, %2 errors, %3 skipped.",
    "formateo de orígenes": "source formatting",
    "apagado del equipo": "computer shutdown",
    "Acciones posteriores bloqueadas": "Post-ingest actions blocked",
    "Hay errores en la ingesta. Por seguridad, se han bloqueado las siguientes acciones:\n• %1": "There were errors during ingest. For safety, the following actions have been blocked:\n• %1",
    "Formatear orígenes": "Format sources",
    "El formateo de tarjetas solo está disponible en Windows.": "Card formatting is only available on Windows.",
    "No hay orígenes que formatear.": "There are no sources to format.",
    "completo": "full",
    "rápido": "quick",
    "Ninguno de los orígenes es una unidad extraíble. No se formateará nada.": "None of the sources is a removable drive. Nothing will be formatted.",
    "Se formatearán las unidades extraíbles (modo %1):": "Removable drives will be formatted (mode %1):",
    "\nSe omitirán (no son unidades extraíbles):": "\nWill be skipped (not removable drives):",
    "\n\n¿Continuar?": "\n\nContinue?",
    "Formateando...": "Formatting...",
    "Formatear": "Format",
    "No se pudo completar el formateo:\n%1": "Formatting could not be completed:\n%1",
    "Formateados %1/%2 con errores": "%1/%2 formatted with errors",
    "Formateados %1/%2.\nErrores:\n%3": "Formatted %1/%2.\nErrors:\n%3",
    "Orígenes formateados: %1/%2": "Sources formatted: %1/%2",
    "Orígenes formateados correctamente: %1/%2.": "Sources formatted successfully: %1/%2.",
    "Apagar ordenador": "Shut down computer",
    "Todas las tareas han finalizado. ¿Apagar el ordenador ahora?": "All tasks have finished. Shut down the computer now?",
    "Apagado programado.": "Shutdown scheduled.",
    "Apagar": "Shut down",
    "No se pudo programar el apagado:\n%1": "Could not schedule the shutdown:\n%1",
    "Renombrar cámara...": "Rename camera...",
    "Sin cámara": "No camera",
    "No se detectó cámara para renombrar.": "No camera was detected to rename.",
    "Renombrar cámara": "Rename camera",
    "Nuevo nombre para '%1':": "New name for '%1':",
    "Cámara renombrada: %1 → %2": "Camera renamed: %1 → %2",
    "Cámara desconocida detectada": "Unknown camera detected",
    "Se detectó '%1' sin identificar.\nIntroduce un nombre para el dispositivo:": "'%1' was detected but not identified.\nEnter a name for the device:",
    "Nombre de la cámara para este origen:": "Camera name for this source:",
    "Cámara: Sin nombre (manual)": "Camera: No name (manual)",
    "Cámara detectada: %1": "Camera detected: %1",
    "Escaneo de cámaras: %1 sesion(es) procesada(s).": "Camera scan: %1 session(s) processed.",
    "Cámara no detectada": "Camera not detected",
    "No se pudo detectar la cámara en %1.": "Could not detect the camera on %1.",
    "¿Qué nombre quieres darle a esta cámara?": "What name do you want to give this camera?",
    "Renombrar…": "Rename…",
    "Nombre de cámara": "Camera name",
    "Introduce el nombre de la cámara:": "Enter the camera name:",
    "Cámara: %1": "Camera: %1",
    "Cámara: Sin nombre": "Camera: No name",
    "Origen asignado a sesión #%1": "Source assigned to session #%1",
    "Sesión auto creada para %1": "Auto session created for %1",
    "Sesión de %1 eliminada.": "Session for %1 deleted.",
    "(Sin sesiones)": "(No sessions)",
    "Origen: %1": "Source: %1",
    "Origen automático: %1": "Automatic source: %1",
    "Origen: sin origen (no se ejecutará)": "Source: no source (will not run)",
    "Nueva Sesión manual": "New Manual Session",
    "Nombre de la sesión:": "Session name:",
    "Sesión manual '%1' creada (ID: %2)": "Manual session '%1' created (ID: %2)",
    "¿Eliminar la sesión #%1 y todos sus archivos?\nEsta acción no se puede deshacer.": "Delete session #%1 and all its files?\nThis action cannot be undone.",
    "Sesión #%1 eliminada.": "Session #%1 deleted.",
    "Seleccionar destino de sesión": "Select session destination",
    "Seleccionar origen de sesión": "Select session source",
    "&Archivo": "&File",
    "&Nuevo Proyecto...": "&New Project...",
    "&Recargar proyectos": "&Reload projects",
    "&Eliminar todos los proyectos...": "&Delete all projects...",
    "&Salir": "&Quit",
    "&Rutas": "&Routes",
    "Seleccionar &origen (SD)...": "Select &source (SD)...",
    "Seleccionar &destino del proyecto...": "Select project &destination...",
    "Auto-detectar &unidades extraíbles al inicio": "Auto-detect &removable drives at startup",
    "&Detectar unidades extraíbles ahora": "&Detect removable drives now",
    "Abrir carpeta &datos...": "Open &data folder...",
    "Gestionar &destinos de volcado...": "Manage &dump destinations...",
    "&Detección": "&Detection",
    "Configurar detección de &cámara...": "Configure &camera detection...",
    "Detectar &información de tarjeta SD...": "Detect &SD card info...",
    "&Personalizado": "&Customize",
    "Personalizar &carpeta de footage...": "Customize &footage folder...",
    "Personalizar &contenedores de archivos...": "Customize &file containers...",
    "&Vista": "&View",
    "Tema": "Theme",
    "Acento": "Accent",
    "Fondo de trigo": "Wheat background",
    "Oscuro": "Dark",
    "Claro": "Light",
    "Neutro": "Neutral",
    "Verde": "Green",
    "Azul": "Blue",
    "Rosa": "Pink",
    "Morado": "Purple",
    "Ámbar": "Amber",
    "A&yuda": "&Help",
    "&Búsqueda de actualizaciones...": "&Check for updates...",
    "&Acerca de...": "&About...",
    "&Idioma": "&Language",
    "Idioma": "Language",
    "Reinicia la aplicación para aplicar el idioma.": "Restart the app to apply the language.",
    "Seleccionar carpeta de la Tarjeta SD": "Select SD Card folder",
    "Selecciona o crea un proyecto antes de cambiar su destino.": "Select or create a project before changing its destination.",
    "Seleccionar carpeta maestra del proyecto": "Select project master folder",
    "Destino maestro actualizado: %1": "Master destination updated: %1",
    "No se pudo actualizar el destino: %1": "Could not update the destination: %1",
    "Selecciona un proyecto para eliminar.": "Select a project to delete.",
    "Confirmar eliminación": "Confirm deletion",
    "¿Eliminar el proyecto #%1 y todos sus datos?\nEsta acción no se puede deshacer.": "Delete project #%1 and all its data?\nThis action cannot be undone.",
    "Eliminado": "Deleted",
    "Proyecto eliminado correctamente.": "Project deleted successfully.",
    "Error al eliminar el proyecto: %1": "Error deleting the project: %1",
    "Sin proyectos": "No projects",
    "No hay proyectos para eliminar.": "There are no projects to delete.",
    "Eliminar todos los proyectos": "Delete all projects",
    "¿Eliminar los %1 proyectos y todos sus datos?\nEsta acción no se puede deshacer.": "Delete the %1 projects and all their data?\nThis action cannot be undone.",
    "Eliminados": "Deleted",
    "Todos los proyectos han sido eliminados.": "All projects have been deleted.",
    "Error al eliminar los proyectos: %1": "Error deleting the projects: %1",
    "Acerca de CosechaMedia": "About CosechaMedia",
    "Herramienta de ingesta de tarjetas SD para producción audiovisual.": "SD card ingest tool for audiovisual production.",
    "El Modo guiado para volcados rápidos estará disponible próximamente.": "Guided mode for quick dumps will be available soon.",
    "Búsqueda de actualizaciones": "Check for updates",
    "La búsqueda de actualizaciones estará disponible próximamente.": "Update checking will be available soon.",
    "Sin origen": "No source",
    "Selecciona o añade una ruta de tarjeta SD primero.": "Select or add an SD card path first.",
    "Marca: %1": "Brand: %1",
    "Modelo: %1": "Model: %1",
    "Serie: %1": "Serial: %1",
    "Capacidad: %1 GB": "Capacity: %1 GB",
    "Sistema: %1": "File system: %1",
    "Uso: %1%": "Usage: %1%",
    "Errores: %1": "Errors: %1",
    "No se pudo detectar información de la tarjeta.": "Could not detect card information.",
    "Información de Tarjeta SD": "SD Card Information",
    "No se detectaron unidades extraíbles.": "No removable drives detected.",
    "Auto-detect: %1 unidad(es) añadida(s).": "Auto-detect: %1 drive(s) added.",
    "Auto-detect: ninguna unidad nueva.": "Auto-detect: no new drives.",
    "Sin ingesta": "No ingest",
    "Realiza una ingesta primero.": "Run an ingest first.",
    "Reorganizar": "Reorganize",
    "¿Reorganizar archivos en 'Unknown_Camera' detectando su cámara por metadatos?": "Reorganize files in 'Unknown_Camera' by detecting their camera via metadata?",
    "Reorganizando...": "Reorganizing...",
    "No se pudo reorganizar:\n%1": "Could not reorganize:\n%1",
    "Hecho": "Done",
    "Archivos reorganizados.": "Files reorganized.",
    "Proxies": "Proxies",
    "No se encontraron clips de video en la ingesta.": "No video clips found in the ingest.",
    "Generar proxies %1p para %2 clips de video?": "Generate %1p proxies for %2 video clips?",
    "Generando proxies...": "Generating proxies...",
    "No se pudieron generar los proxies:\n%1": "Could not generate the proxies:\n%1",
    "Proxies generados: %1": "Proxies generated: %1",
    "Nuevo Proyecto": "New Project",
    "Nombre del Proyecto": "Project Name",
    "Ej: Rodaje_Cine_01": "E.g. Shoot_Film_01",
    "Descripción (Opcional)": "Description (Optional)",
    "Breve descripción del proyecto...": "Brief project description...",
    "Ruta de Destino": "Destination Path",
    "Ej: H:/Produccion/Proyectos": "E.g. H:/Production/Projects",
    "Duración": "Duration",
    "Todos los archivos pertenecen al mismo día": "All files belong to the same day",
    "Los archivos se organizarán por fecha de rodaje": "Files will be organized by shoot date",
    "No se usará fecha para organizar los archivos": "No date will be used to organize the files",
    "Organización": "Organization",
    "Cámara primero (Cámara/Fecha)": "Camera first (Camera/Date)",
    "Fecha primero (Fecha/Cámara)": "Date first (Date/Camera)",
    "Solo por cámara": "Camera only",
    "Usar fecha de metadatos": "Use metadata date",
    "Usar las fechas de los archivos en lugar de la fecha manual": "Use file dates instead of the manual date",
    "Crear Proyecto": "Create Project",
    "Debes poner un nombre y una ruta de destino.": "You must provide a name and a destination path.",
    "No se pudo guardar el proyecto: %1": "Could not save the project: %1",
    "Solo se admiten letras de unidad de Windows en este momento.": "Only Windows drive letters are supported at the moment.",
    "Formateando %1 (%2/%3)...": "Formatting %1 (%2/%3)...",
    "Proxy %1/%2: %3": "Proxy %1/%2: %3",
    "Reorganizando ingesta %1/%2...": "Reorganizing ingest %1/%2...",
    "El repositorio aún no ha publicado versiones.": "The repository has not published any releases yet.",
    "No se pudo obtener la suma SHA-256 del paquete.": "Could not fetch the SHA-256 checksum of the package.",
    "La descarga no coincide con la suma SHA-256. Inténtalo de nuevo.": "The download does not match the SHA-256 checksum. Try again.",
    "La actualización solo puede instalarse desde la aplicación empaquetada.": "The update can only be installed from the packaged app.",
    "No se encontró la aplicación CosechaMedia en este sistema.": "Could not find the CosechaMedia app on this system.",
    "La ubicación actual de la aplicación no es escribible. Mueve CosechaMedia.app a /Applications y vuelve a intentarlo.": "The current location of the app is not writable. Move CosechaMedia.app to /Applications and try again.",
    "El paquete de actualización no contiene una aplicación válida.": "The update package does not contain a valid app.",
    "Acerca de": "About",
    "Actualizaciones": "Updates",
    "Versión: %1": "Version: %1",
    "Versión instalada: %1": "Installed version: %1",
    "Desarrollado por %1": "Developed by %1",
    "Comprobar ahora": "Check now",
    "Descargar e instalar": "Download and install",
    "Buscar actualizaciones al inicio": "Check for updates at startup",
    "Comprobando actualizaciones...": "Checking for updates...",
    "Tienes la última versión instalada (%1).": "You have the latest version installed (%1).",
    "No hay un paquete de actualización para tu sistema.": "There is no update package for your system.",
    "Nueva versión disponible: %1 (actual: %2).": "New version available: %1 (current: %2).",
    "No se pudo comprobar las actualizaciones: %1": "Could not check for updates: %1",
    "Descargando %1...": "Downloading %1...",
    "Descarga completada y verificada. La actualización se instalará al reiniciar.": "Download complete and verified. The update will be installed on restart.",
    "No se pudo descargar la actualización: %1": "Could not download the update: %1",
    "Instalar actualización": "Install update",
    "La aplicación se cerrará para instalar la nueva versión. ¿Continuar?": "The app will close to install the new version. Continue?",
    "No se pudo instalar la actualización: %1": "Could not install the update: %1",
    "Actualización disponible": "Update available",
    "Hay una nueva versión de CosechaMedia disponible: %1. ¿Quieres ver los detalles?": "A new version of CosechaMedia is available: %1. Would you like to see the details?",
    "Seleccionar carpeta": "Select folder",
    "📅 Volcado por fecha": "📅 Dump by date",
    "Volcado selectivo de tarjetas 'sucias' o smartphones agrupado por día de grabación": "Selective dump of 'dirty' cards or smartphones grouped by recording day",
    "Selecciona o crea un proyecto antes de hacer un volcado selectivo.": "Select or create a project before doing a selective dump.",
    "Volcado selectivo por fecha": "Selective dump by date",
    "Para tarjetas que acumulan grabaciones de distintos días (p. ej. smartphones). Escanea el origen, agrupa los archivos por día de grabación y te deja elegir qué días volcar. La copia es verificada por MD5.": "For cards that accumulate recordings from different days (e.g. smartphones). Scans the source, groups files by recording day and lets you choose which days to dump. The copy is verified with MD5.",
    "Origen": "Source",
    "Ruta de la tarjeta o del teléfono...": "Card or phone path...",
    "Destino (organización del proyecto)": "Destination (project organization)",
    "Carpeta maestra del proyecto...": "Project master folder...",
    "Los archivos se colocarán bajo %1 en subcarpetas de cámara y día.": "Files will be placed under %1 in camera and day subfolders.",
    "Escanear": "Scan",
    "Escaneando...": "Scanning...",
    "Volcando...": "Dumping...",
    "Detener": "Stop",
    "con archivos": "with files",
    "seleccionado": "selected",
    "Seleccionar todo": "Select all",
    "Limpiar": "Clear",
    "Clic: seleccionar · Ctrl: añadir/quitar · Shift o arrastre: rango": "Click: select · Ctrl: add/remove · Shift or drag: range",
    "Archivos de los días seleccionados:": "Files from the selected days:",
    "Fecha": "Date",
    "Tamaño": "Size",
    "Tipo": "Type",
    "Incluir archivos sin fecha (se volcarán con la fecha de hoy)": "Include files without date (they will be dumped with today's date)",
    "Volcar selección": "Dump selection",
    "Origen inválido": "Invalid source",
    "Introduce una carpeta de origen válida.": "Enter a valid source folder.",
    "Destino inválido": "Invalid destination",
    "Introduce la carpeta de destino del proyecto.": "Enter the project destination folder.",
    "No se pudo escanear el origen: %1": "Could not scan the source: %1",
    "%1 archivos en %2 día(s) de grabación": "%1 files on %2 recording day(s)",
    "%1 archivos en %2 día(s) de grabación · %3 sin fecha": "%1 files on %2 recording day(s) · %3 without date",
    "%1 archivos · %2 · %3 día(s) seleccionado(s)": "%1 files · %2 · %3 selected day(s)",
    "Sin archivos": "No files",
    "No hay archivos seleccionados para volcar.": "There are no files selected to dump.",
    "Volcado selectivo %1": "Selective dump %1",
    "El volcado no pudo completarse: %1": "The dump could not be completed: %1",
    "Volcado detenido": "Dump stopped",
    "Cancelando…": "Cancelling…",
    "Volcado detenido por el usuario.\n%1 procesados, %2 errores.": "Dump stopped by the user.\n%1 processed, %2 errors.",
    "Volcado completado": "Dump complete",
    "Volcado selectivo finalizado.\n\n%1 archivos volcados correctamente.\n%2 errores.": "Selective dump finished.\n\n%1 files dumped successfully.\n%2 errors.",
    "Contenido": "Content",
    "Todo": "All",
    "Seleccionar contenido del origen": "Select source content",
    "Aplicar selección": "Apply selection",
    "el %1": "the %1",
    "del %1 al %2": "from %1 to %2",
    "%1 días": "%1 days",
    "sin fecha": "without date",
    "Solo sin fecha": "Only without date",
    "Activa el origen para configurar su contenido.": "Activate the source to configure its content.",
    "El origen '%1' ya está en la lista.": "The source '%1' is already in the list.",
    "Origen cambiado: %1": "Source changed: %1",
    "Contenido del origen %1: %2": "Content of source %1: %2",

    # --- Dispositivos MTP ---
    "Dispositivo…": "Device…",
    "Importar desde dispositivo (MTP)…": "Import from device (MTP)…",
    "Importar desde un móvil o cámara conectado por USB (MTP)": "Import from a phone or camera connected via USB (MTP)",
    "Seleccionar carpeta del dispositivo": "Select device folder",
    "Conecta el móvil o la cámara por USB y elige la carpeta a importar.": "Connect your phone or camera via USB and choose the folder to import.",
    "Dispositivo:": "Device:",
    "Dispositivo": "Device",
    "Actualizar": "Refresh",
    "Aceptar": "OK",
    "No se detectó ningún dispositivo. Revisa el cable y pulsa Actualizar.": "No device detected. Check the cable and press Refresh.",
    "Cargando…": "Loading…",
    "No se pudo leer el dispositivo: %1": "Could not read the device: %1",
    "Selecciona o crea un proyecto antes de elegir un dispositivo.": "Select or create a project before choosing a device.",
    "Sincronizando %1 (%2/%3)…": "Syncing %1 (%2/%3)…",
    "Sincronizando dispositivo (primera pasada)…": "Syncing device (first pass)…",
    "No se pudo sincronizar el dispositivo: %1": "Could not sync the device: %1",
    "Dispositivo sincronizado: %1 nuevos, %2 sin cambios, %3 errores.": "Device synced: %1 new, %2 unchanged, %3 errors.",
    "Dispositivos guardados...": "Saved devices...",
    "Dispositivos guardados": "Saved devices",
    "Eliminar un dispositivo borra también sus sesiones y archivos registrados.": "Deleting a device also removes its sessions and registered files.",
    "Eliminar dispositivo": "Delete device",
    "¿Eliminar este dispositivo y todas sus sesiones?": "Delete this device and all its sessions?",

    # --- Ingesta por WiFi (FTP) ---
    "Importar por WiFi (FTP)": "Import via WiFi (FTP)",
    "Conecta el móvil o la cámara al mismo WiFi que el ordenador, "
    "inicia el servidor FTP en el dispositivo y configura la conexión.": "Connect your phone or camera to the same WiFi as this computer, "
    "start the FTP server on the device and set up the connection.",
    "Servidor guardado:": "Saved server:",
    "Nombre:": "Name:",
    "Servidor (IP):": "Server (IP):",
    "Puerto:": "Port:",
    "Usuario:": "User:",
    "Contraseña:": "Password:",
    "(opcional)": "(optional)",
    "Carpeta base:": "Base folder:",
    "Conectar": "Connect",
    "Cómo conectar (guía paso a paso)": "How to connect (step-by-step guide)",
    "Guía de conexión (apps FTP recomendadas)": "Connection guide (recommended FTP apps)",
    "— Añadir nuevo servidor —": "— Add new server —",
    "Introduce la IP o nombre del servidor.": "Enter the server IP or hostname.",
    "No se pudo guardar el perfil: %1": "Could not save the profile: %1",
    "Conectando…": "Connecting…",
    "No se pudo conectar: %1": "Could not connect: %1",
    "Conectado. Elige la carpeta a importar.": "Connected. Choose the folder to import.",
    "WiFi (FTP)…": "WiFi (FTP)…",
    "Importar desde un móvil o cámara por WiFi (FTP)": "Import from a phone or camera via WiFi (FTP)",
    "Dispositivo no disponible": "Device not available",
    "Modo pasivo (recomendado)": "Passive mode (recommended)",
    "Detectar en la red…": "Detect on the network…",
    "Busca servidores FTP en tu red WiFi": "Search for FTP servers on your WiFi network",
    "Escaneando la red…": "Scanning the network…",
    "No se encontraron servidores FTP en la red. Comprueba que el servidor está iniciado.": "No FTP servers found on the network. Check that the server is running.",
    "Servidores FTP encontrados": "FTP servers found",
    "Elige tu dispositivo:": "Choose your device:",
    "Servidor encontrado: %1": "Server found: %1",
    "Conectado en modo activo. Elige la carpeta a importar.": "Connected in active mode. Choose the folder to import.",
    "Conectado en modo pasivo. Elige la carpeta a importar.": "Connected in passive mode. Choose the folder to import.",
    "Android — Primitive FTPd (recomendada):\n"
    "1. Instala Primitive FTPd desde F-Droid o github.com/wolpi/prim-ftpd "
    "(gratis, código abierto; ya no está en Google Play).\n"
    "2. Ábrela y pulsa ▶ para iniciar el servidor. Concede el acceso a los "
    "archivos si el sistema lo pide.\n"
    "3. La pantalla principal muestra la dirección, p. ej. "
    "ftp://192.168.1.5:2221, y el usuario (por defecto «user»).\n"
    "4. Para poner contraseña, ajústala en los ajustes (engranaje) antes de "
    "iniciar el servidor.\n\n"
    "iOS — GoFTP Server (App Store):\n"
    "1. Instala GoFTP Server desde la App Store y ábrela.\n"
    "2. Pulsa Start. Anota la dirección, el puerto, el usuario y la "
    "contraseña que muestra.\n\n"
    "En CosechaMedia:\n"
    "• Pulsa 'Detectar en la red…' para encontrar el servidor, o escribe la "
    "IP y el puerto.\n"
    "• Introduce usuario y contraseña y pulsa Conectar.\n"
    "• Elige la carpeta (p. ej. DCIM) y pulsa Aceptar.\n"
    "Mantén la pantalla del dispositivo encendida durante la transferencia.": "Android — Primitive FTPd (recommended):\n"
    "1. Install Primitive FTPd from F-Droid or github.com/wolpi/prim-ftpd "
    "(free, open source; no longer on Google Play).\n"
    "2. Open it and press ▶ to start the server. Grant file access if the "
    "system asks.\n"
    "3. The main screen shows the address, e.g. ftp://192.168.1.5:2221, and "
    "the user (default \"user\").\n"
    "4. To set a password, adjust it in Settings (gear) before starting the "
    "server.\n\n"
    "iOS — GoFTP Server (App Store):\n"
    "1. Install GoFTP Server from the App Store and open it.\n"
    "2. Press Start. Note the address, port, user and password it shows.\n\n"
    "In CosechaMedia:\n"
    "• Press 'Detect on the network…' to find the server, or type the IP and "
    "port.\n"
    "• Enter user and password and press Connect.\n"
    "• Choose the folder (e.g. DCIM) and press OK.\n"
    "Keep the device screen on during the transfer.",

    # --- Recepción por WiFi (buzón QR) ---
    "Recibir por WiFi": "Receive via WiFi",
    "¿Cómo quieres recibir los archivos de los móviles?": "How do you want to receive files from the phones?",
    "PairDrop": "PairDrop",
    "Compatible con Android/iOS. Sin instalar nada en el móvil: "
    "escanea el código QR y envía los archivos.": "Works with Android/iOS. Nothing to install on the phone: "
    "scan the QR code and send the files.",
    "FTP Clásico": "Classic FTP",
    "Avanzado. El dispositivo ejecuta un servidor FTP "
    "(requiere una app y configuración en el móvil).": "Advanced. The device runs an FTP server "
    "(requires an app and setup on the phone).",
    "WiFi…": "WiFi…",
    "Recibir archivos de un móvil por WiFi (QR o FTP)": "Receive files from a phone over WiFi (QR or FTP)",
    "Inbox WiFi": "WiFi Inbox",
    "Recibir por WiFi (PairDrop)": "Receive via WiFi (PairDrop)",
    "Cada persona escanea su código QR desde el móvil y envía "
    "los archivos sin instalar nada. El móvil y el ordenador "
    "deben estar en la misma red WiFi. Al llegar, "
    "CosechaMedia los guarda en la caché del origen y los "
    "vuelca verificados al proyecto según llegan.": "Each person scans their QR code from their phone and sends "
    "the files without installing anything. The phone and the computer "
    "must be on the same WiFi network. When they arrive, "
    "CosechaMedia saves them to the source cache and dumps them to the "
    "project (verified) as they come in.",
    "Escanea este código QR desde el móvil para enviar "
    "archivos sin instalar nada. El móvil y el ordenador "
    "deben estar en la misma red WiFi.": "Scan this QR code from your phone to send "
    "files without installing anything. The phone and the computer "
    "must be on the same WiFi network.",
    "Remitente:": "Sender:",
    "Remitente": "Sender",
    "Ubicación": "Location",
    "Añadir": "Add",
    "Editar": "Edit",
    "Eliminar": "Delete",
    "Enviar una carpeta entera (modo carpeta)": "Send a whole folder (folder mode)",
    "Copiar": "Copy",
    "Copiado": "Copied",
    "Copiar enlace": "Copy link",
    "Cerrar": "Close",
    "Detener": "Stop",
    "El servidor no está activo.": "The server is not active.",
    "No se pudo iniciar el servidor: %1": "Could not start the server: %1",
    "Servidor activo. Comparte esta dirección con los móviles: "
    "%1": "Server active. Share this address with the phones: %1",
    "Añadir remitente WiFi": "Add WiFi sender",
    "Añadir remitente WiFi…": "Add WiFi sender…",
    "Nombre de la persona (aparecerá en el código QR):": "Person's name (it will appear in the QR code):",
    "Ubicación (destino personalizado de la ingesta; "
    "en blanco usa la ruta maestra del proyecto):": "Location (custom ingest destination; "
    "blank uses the project master path):",
    "En blanco: ruta maestra del proyecto": "Blank: project master path",
    "Examinar…": "Browse…",
    "Seleccionar ubicación": "Select location",
    "Eliminar origen": "Delete source",
    "¿Eliminar el origen '%1' y sus sesiones (%2)?": "Delete the source '%1' and its sessions (%2)?",
    "Origen eliminado: %1": "Source deleted: %1",
    "Recibido de %1: %2 (%3).": "Received from %1: %2 (%3).",
    "Recepción detenida. Pulsa «WiFi…» para reanudarla.": "Reception stopped. Press “WiFi…” to resume.",
    "Recepción detenida. Pulsa «Reanudar» para continuar.": "Reception stopped. Press “Resume” to continue.",
    "Recepción WiFi detenida.": "WiFi reception stopped.",
    "Recepción WiFi reanudada.": "WiFi reception resumed.",
    "Reanudar": "Resume",
    "Añadir dispositivo WiFi": "Add WiFi device",
    "Añadir dispositivo WiFi…": "Add WiFi device…",
    "Nombre del dispositivo (aparecerá en el código QR):": "Device name (it will appear in the QR code):",
    "Ej.: Móvil de Joan": "E.g. Joan's phone",
    "Mostrar el código QR de este dispositivo": "Show the QR code for this device",
    "Configurar este origen FTP": "Configure this FTP source",
    "FTP": "FTP",
    "QR": "QR",
    "Origen habilitado: %1": "Source enabled: %1",
    "Origen deshabilitado: %1": "Source disabled: %1",
    "Eliminar completados": "Delete completed",
    "Eliminar de la tabla de ingesta": "Remove from the ingest table",
    "Archivos completados eliminados de la tabla de ingesta: %1.": "Completed files removed from the ingest table: %1.",
    "Cambiar carpeta maestra": "Change master folder",
    "Mover a la nueva ubicación": "Move to the new location",
    "Dejar como están": "Leave as is",
    "¿Qué quieres hacer con ellos?": "What do you want to do with them?",
    "La carpeta maestra tiene %1 archivo(s) completado(s) en la ubicación anterior (%2).": "The master folder has %1 completed file(s) in the previous location (%2).",
    "Archivos movidos a la nueva carpeta maestra: %1 (%2 con errores).": "Files moved to the new master folder: %1 (%2 with errors).",
    "WiFi": "WiFi",
    "Proyecto por defecto": "Default project",
    "Proyecto creado automáticamente": "Project created automatically",
    "Proyecto por defecto creado con sesión inicial.": "Default project created with initial session.",
    "Sesión 1": "Session 1",
    "No se pudo crear el proyecto por defecto: %1": "Could not create the default project: %1",
}


def _escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _serialize_message(msg, missing):
    source = msg.findtext("source")
    translation = TRANSLATIONS.get(source, missing)
    lines = ["    <message>"]
    for loc in msg.findall("location"):
        fn = loc.get("filename")
        ln = loc.get("line", "")
        lines.append(f'        <location filename="{_escape(fn)}" line="{ln}"/>')
    lines.append(f"        <source>{_escape(source)}</source>")
    if translation is None:
        lines.append('        <translation type="unfinished"></translation>')
    else:
        lines.append(f"        <translation>{_escape(translation)}</translation>")
    lines.append("    </message>")
    return "\n".join(lines)


def main():
    tree = ET.parse(TS_PATH)
    root = tree.getroot()
    contexts = []
    missing = []
    for context in root.findall("context"):
        name = context.findtext("name") or ""
        messages = []
        for msg in context.findall("message"):
            trans = msg.find("translation")
            if trans is not None and trans.get("type") in ("obsolete", "vanished"):
                continue
            source = msg.findtext("source")
            if source is not None and source not in TRANSLATIONS:
                missing.append(source)
            messages.append(_serialize_message(msg, None))
        contexts.append((name, messages))

    if missing:
        print("MISSING TRANSLATIONS:")
        for m in sorted(set(missing)):
            print("  -", repr(m))
        sys.exit(1)

    parts = ['<?xml version="1.0" encoding="utf-8"?>', "<!DOCTYPE TS>",
             '<TS version="2.1" language="en_US">']
    for name, messages in contexts:
        parts.append("<context>")
        parts.append(f"    <name>{_escape(name)}</name>")
        parts.extend(messages)
        parts.append("</context>")
    parts.append("</TS>")
    with open(TS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print("OK: translations written to", TS_PATH)


if __name__ == "__main__":
    main()
