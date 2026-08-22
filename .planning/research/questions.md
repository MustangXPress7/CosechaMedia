# Research Questions

Preguntas abiertas que necesitan investigación más profunda. Añadir entradas con fecha y contexto.

---

## 2026-08-22 — Estado de SHA-256 en la spec ASC MHL

**Pregunta:** ¿La especificación ASC MHL contempla `sha256` como hashFormat (aunque la implementación de referencia v1.2 no lo soporte)? ¿Existe intención upstream (`ascmitc/mhl`) de añadirlo?

**Contexto:** Durante el diseño de la fase XXH64+ASC MHL se verificó que el paquete oficial implementa `md5, sha1, xxh32, xxh64, xxh3, xxh128, c4` pero no SHA-256. El nivel "Máxima" de CosechaMedia usa sidecars `.sha256` propios fuera del estándar como workaround. La respuesta determina si ese workaround es temporal (contribución upstream viable, ver seed) o permanente.

**Impacto si la respuesta es favorable:** manifiestos de archivado 100% estándar, se eliminan los sidecars paralelos.
