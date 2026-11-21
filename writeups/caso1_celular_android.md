# Caso 1 — Estafa por venta de moto (Android)

**Contexto.** Una denunciante pagó $850.000 por una moto publicada en Marketplace que nunca recibió.
Se secuestró el celular del sospechoso y se calcularon los SHA-256 en el lugar del hecho.
Puntos de pericia: **a)** ¿hay comunicaciones con la denunciante? **b)** ¿participó otra persona?
**c)** ¿a qué cuenta fue el dinero? **d)** ¿la evidencia está íntegra?

Todo el análisis se hizo sobre una copia (`trabajo/`). Horas en UTC-3.

---

## 1.1 Cadena de custodia

```bash
python hash_lote.py ../trabajo/caso1_celular_android --verificar ../trabajo/caso1_acta_secuestro_hashes.txt
cd ../trabajo/caso1_celular_android && sha256sum -c ../caso1_acta_secuestro_hashes.txt
```

Las dos herramientas coinciden: **6 OK, 1 alterado** →
`sdcard/DCIM/Camera/IMG_20261106_181502.jpg` (acta `2cea1522…`, actual `561b40a1…`).
El original y la copia tienen el mismo hash: la alteración es previa a la pericia, posterior al acta.
→ [verificacion_hashes.txt](../resultados/caso1_celular/verificacion_hashes.txt)

**Criterio:** no se descarta toda la extracción. Los otros 6 archivos están íntegros; el alterado se
informa, se excluye de las conclusiones y se pone en conocimiento de la Fiscalía.

## 1.2 Identificación del equipo (`system/build.prop`)

| Dato | Valor |
|---|---|
| Modelo | Samsung SM-A546E (Galaxy A54 5G) |
| Android | 14, parche 2026-09-01 |
| Serie | R58TA0FICT1 |
| Zona horaria | America/Argentina/Salta |

La zona horaria define cómo interpretar las fechas EXIF; el parche condiciona qué tipo de extracción
es posible (lógica / sistema de archivos / física).

## 1.3 WhatsApp

```bash
python whatsapp_parser.py --msgstore .../msgstore.db --wa .../wa.db -o salida_wa
```

15 mensajes en 3 chats → [mensajes.csv](../resultados/caso1_celular/mensajes.csv) ·
[informe_whatsapp.html](../resultados/caso1_celular/informe_whatsapp.html).
Verificado a mano con SQL:

```sql
SELECT _id, chat_row_id, from_me, datetime(timestamp/1000,'unixepoch','-3 hours'), text_data
FROM message ORDER BY timestamp;
```

| Chat | Contacto | Número | Mensajes |
|---|---|---|---|
| 1 | Carla Compradora | +5493870001111 | 9 — la venta, la transferencia, la cita incumplida |
| 2 | Primo Nacho | +5493870002222 | 4 — "la cuenta de siempre", "sacala hoy", "retirado" |
| 3 | Mamá | +5493870003333 | 2 — sin relevancia |

Los chats 1 y 2 se intercalan minuto a minuto (18:17 → 18:20; 15:44 → 15:45), lo que responde **b)**.
El nombre de agenda no prueba identidad: lo que vale es el número (titularidad → empresa telefónica).

## 1.4 Mensaje eliminado

```bash
python sqlite_borrados.py .../msgstore.db
```

→ [registros_borrados.txt](../resultados/caso1_celular/registros_borrados.txt)

> "Pasale este alias a la mina: SOL.RIO.CAMPO  CVU 0000003100099887766554 titular Rocio Benitez"

El texto solo no dice de qué chat era, así que **decodifiqué la celda SQLite** en `0x3A1A` (página 4):

```
81 07 | 10 | 0b | 00 01 08 33 05 05 08 81 45 08 | 02 | 3EB0DELETED… | 01a19e24e320 | …
largo   id   hdr  tipos de columna               chat   key_id         timestamp
```

| Campo | Valor |
|---|---|
| `_id` | 16 — justo el "próximo id esperado" que reporta el parser |
| `chat_row_id` | **2 (Primo Nacho)** |
| `from_me` | 0 → recibido |
| `timestamp` | 1793654580000 → **02/11/2026 18:23:00** |
| `text_data` | 92 caracteres = largo del texto recuperado ✓ |

**Por qué sigue ahí:** era la celda más reciente de la página. Al borrarla, SQLite quitó el puntero y
corrió el inicio del área de contenido (`0x0AA3`), dejando los bytes en el espacio no asignado
(sin freeblock ni página en freelist). Como se borró el último `_id`, **no queda hueco en la numeración**.

**Limitación:** prueba que el registro existió, no quién lo borró ni cuándo.

## 1.5 Fotos

```bash
python exif_gps.py ../trabajo/caso1_celular_android/sdcard --csv fotos.csv
```

→ [fotos.csv](../resultados/caso1_celular/fotos.csv)

| Archivo | Contenido | EXIF | GPS |
|---|---|---|---|
| IMG_20261101_102233 | moto | 01/11 10:22:33 ✓ | Salta capital |
| IMG_20261104_130010 | almuerzo | 04/11 13:00:10 ✓ | — |
| IMG_20261106_181502 | plaza | **05/11 09:00:00** ✗ | Cerrillos |
| Screenshot_20261103_153112_WhatsApp | comprobante $850.000 a SOL.RIO.CAMPO, "R. Benitez", 03/11 15:29 | — | — |

- La foto de la plaza tiene **nombre** del 06/11 18:15:02 (hora de la cita, en Cerrillos), **EXIF**
  redondo del día anterior y **hash** distinto al acta → metadatos manipulados después del secuestro;
  no se usan para concluir.
- La captura confirma la cuenta del mensaje eliminado por una **fuente independiente** → punto **c)**.

## 1.6 Línea de tiempo

```bash
python linea_tiempo.py --wa salida_wa/mensajes.csv --fotos fotos.csv \
  --manual eventos_manuales.csv --alterados IMG_20261106_181502.jpg
```

→ [linea_tiempo.csv](../resultados/caso1_celular/linea_tiempo.csv) (23 eventos). El script nunca elige
en silencio entre dos fechas contradictorias: la foto alterada aparece dos veces, marcada como
DISCREPANCIA.

## Respuestas

| Punto | Respuesta |
|---|---|
| a) | Sí: 9 mensajes con +5493870001111 sobre la venta y la transferencia |
| b) | Sí: +5493870002222 indica la cuenta y confirma el retiro del dinero |
| c) | Alias SOL.RIO.CAMPO, CVU 0000003100099887766554, titular "Rocio Benitez" (según mensaje y captura; titularidad a confirmar con la entidad) |
| d) | Íntegra salvo `IMG_20261106_181502.jpg`, modificado después del acta |

Informe completo: [informe/informe_pericial_caso1.md](../informe/informe_pericial_caso1.md)
