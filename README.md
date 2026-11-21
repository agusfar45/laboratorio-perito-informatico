# Laboratorio de práctica — Perito Informático

Tres casos forenses simulados resueltos de punta a punta: **un celular Android** (WhatsApp, fotos,
mensajes borrados), **un pendrive formateado** (file carving) y **un servidor Linux comprometido**
(análisis de `auth.log`). Incluye las herramientas en Python, los resultados y un **informe pericial**
redactado con la estructura habitual de la justicia argentina.

> **Todo es ficticio:** personas, números de teléfono, cuentas, comprobantes y CVU.
> Las IPs públicas son de los rangos reservados para documentación (RFC 5737).

## Resultados en una línea

| Caso | Pregunta | Hallazgo principal |
|---|---|---|
| 1 — Celular | ¿A qué cuenta fue el dinero de la estafa? | Recuperé un **mensaje de WhatsApp eliminado** del espacio no asignado de SQLite, lo decodifiqué byte a byte (chat, remitente, hora) y lo crucé con una captura de pantalla |
| 1 — Celular | ¿La evidencia está íntegra? | 1 de 7 archivos **no coincide con el hash del acta** y tiene la fecha EXIF manipulada |
| 2 — Pendrive | ¿Qué tenía el pendrive "vacío"? | 5 archivos recuperados por carving, uno **parcialmente sobrescrito**; vinculan el pendrive con el caso 1 |
| 3 — Servidor | ¿Cómo entraron y qué se llevaron? | Fuerza bruta SSH distribuida desde 3 IPs → acceso como `backup` → usuario persistente con sudo → **exfiltración** de `/srv/clientes` por HTTP → borrado de logs |

## Contenido

```
evidencia/        Evidencia simulada (extracción Android, imagen .dd, auth.log) + acta con hashes
scripts/          Herramientas en Python (solo librería estándar + Pillow)
resultados/       Salidas de cada herramienta, caso por caso
writeups/         Análisis de cada caso: qué hice, con qué comando y qué concluyo
informe/          Informe pericial del Caso 1 (estructura de informe judicial)
ENUNCIADO.md      Consigna original del laboratorio
```

| Write-up | Temas |
|---|---|
| [Caso 1 — Estafa por venta de moto](writeups/caso1_celular_android.md) | Cadena de custodia, `build.prop`, SQLite/WhatsApp, recuperación de registros eliminados, EXIF/GPS, línea de tiempo |
| [Caso 2 — Pendrive formateado](writeups/caso2_pendrive.md) | Imagen forense, firmas de archivo, file carving, archivos fragmentados |
| [Caso 3 — Servidor hackeado](writeups/caso3_servidor.md) | Logs de Linux, fuerza bruta SSH, escalada con sudo, exfiltración, antiforense, recomendaciones |
| [Informe pericial — Caso 1](informe/informe_pericial_caso1.md) | Encabezado, puntos de pericia, metodología (ISO/IEC 27037, IRAM 36100), resultados, conclusiones, anexos |

## Herramientas

| Script | Qué hace |
|---|---|
| `hash_lote.py` | Calcula y verifica SHA-256/MD5 contra un manifiesto (compatible con `sha256sum -c`) |
| `whatsapp_parser.py` | Extrae chats de `msgstore.db` + contactos de `wa.db` → CSV + informe HTML, abriendo la base en solo lectura |
| `sqlite_borrados.py` | Busca texto de registros eliminados en el archivo SQLite crudo |
| `exif_gps.py` | Extrae equipo, fechas y GPS de fotos JPEG |
| `carving.py` | File carving por firmas (JPEG, PNG, PDF) sobre imágenes crudas |
| `auth_log.py` | Detecta fuerza bruta, accesos tras fallos y comandos sudo en `auth.log` |
| `linea_tiempo.py` | Une mensajes, fotos y eventos manuales en una línea de tiempo UTC-3, marcando discrepancias |

Uso rápido (Python 3.8+, `pip install pillow`):

```bash
cd scripts
python hash_lote.py ../evidencia/caso1_celular_android --verificar ../evidencia/caso1_acta_secuestro_hashes.txt
python whatsapp_parser.py --msgstore ../evidencia/caso1_celular_android/data/data/com.whatsapp/databases/msgstore.db \
                          --wa ../evidencia/caso1_celular_android/data/data/com.whatsapp/databases/wa.db -o salida_wa
python carving.py ../evidencia/caso2_pendrive.dd -o recuperados
python auth_log.py ../evidencia/caso3_servidor/auth.log
```

## Principios que apliqué

1. **Nunca sobre el original:** todo el análisis se hizo sobre una copia de trabajo.
2. **Hash antes y después:** las bases SQLite se abren con `mode=ro&immutable=1` y el SHA-256 se verifica al final.
3. **Cada herramienta, verificada con otra:** script propio vs. `sha256sum -c`, consultas SQL a mano, `xxd`, `grep`.
   Así encontré, por ejemplo, que `auth_log.py` y `grep "Failed password"` cuentan distinto y por qué.
4. **Horario explícito:** WhatsApp guarda UTC en milisegundos; EXIF guarda hora local sin zona; syslog no guarda ni año ni zona.
5. **Imparcialidad:** el informe describe hechos técnicos y sus limitaciones; no opina sobre culpabilidad.

## Lo que sigue

- Repetir el caso 2 con Foremost, binwalk y The Sleuth Kit/Autopsy y comparar resultados.
- Analizar extracciones Android reales (de mi propio teléfono) con ALEAPP.
- Contar intentos SSH por PID de `sshd` en `auth_log.py` para no duplicar los `Invalid user`.
