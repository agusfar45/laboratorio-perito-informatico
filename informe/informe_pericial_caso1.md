# Informe pericial — Caso 1 (práctica)

**EJERCICIO DE PRÁCTICA. Todos los datos son ficticios y no tienen validez legal.**

## 1. Encabezado

| Campo | Dato |
| --- | --- |
| Autos / Expediente | Caso PRACTICA-2026-0147, "Denuncia por estafa — venta de motocicleta" |
| Dependencia | Fiscalía Penal (ficticia), Salta |
| Perito | (nombre del perito), Perito Informático |
| Fecha del informe | 21/11/2026 |
| Horario utilizado | Todas las horas se expresan en hora oficial argentina (UTC-3), salvo indicación en contrario |

## 2. Objeto de la pericia

La Fiscalía solicita que se determine, sobre el teléfono secuestrado al imputado:

- **a)** Si existen comunicaciones con la denunciante.
- **b)** Si participó otra persona.
- **c)** A qué cuenta se envió el dinero.
- **d)** Si la evidencia se encuentra íntegra.

## 3. Elementos recibidos

Se recibió una extracción lógica de un teléfono celular, junto con el acta de secuestro del 07/11/2026 a las 10:40, que consigna los SHA-256 calculados en el lugar del hecho.

| Dato | Valor | Fuente |
| --- | --- | --- |
| Marca y modelo | Samsung SM-A546E (Galaxy A54 5G) | `system/build.prop` |
| Sistema operativo | Android 14, parche de seguridad 01/09/2026 | `system/build.prop` |
| Número de serie | R58TA0FICT1 | `ro.serialno` |
| Zona horaria configurada | America/Argentina/Salta (UTC-3) | `persist.sys.timezone` |

**Archivos de la extracción y verificación contra el acta (SHA-256):**

| Archivo | SHA-256 según acta | Resultado |
| --- | --- | --- |
| data/data/com.whatsapp/databases/msgstore.db | 610f9604…af63b | Coincide |
| data/data/com.whatsapp/databases/wa.db | 8e2152df…cb86 | Coincide |
| sdcard/DCIM/Camera/IMG_20261101_102233.jpg | f56bd0fa…922c | Coincide |
| sdcard/DCIM/Camera/IMG_20261104_130010.jpg | dad8e131…3b02b | Coincide |
| sdcard/DCIM/Camera/IMG_20261106_181502.jpg | 2cea1522…3500 | **No coincide** (actual: 561b40a1…15a5) |
| sdcard/Pictures/Screenshots/Screenshot_20261103_153112_WhatsApp.jpg | dac8cc31…2f33 | Coincide |
| system/build.prop | bcbf0b32…c9f | Coincide |

Los valores completos de los hashes figuran en el Anexo A. Queda pendiente constatar que el número de serie coincida con el del acta y con la etiqueta física del equipo.

## 4. Metodología y herramientas

Se trabajó sobre una copia de la extracción y nunca sobre el original, siguiendo los lineamientos de la norma ISO/IEC 27037 y la IRAM 36100 para la preservación de evidencia digital. Antes y después de cada análisis se calculó el hash para verificar que la evidencia no se alterara. Las bases SQLite se abrieron en modo solo lectura (`mode=ro&immutable=1`).

| Herramienta | Versión | Uso |
| --- | --- | --- |
| GNU coreutils `sha256sum` | (consignar con `sha256sum --version`) | Cálculo y verificación de hashes |
| Python | 3.11.9 | Intérprete de los scripts de análisis |
| SQLite (módulo `sqlite3` de Python) | (consignar con `sqlite3.sqlite_version`) | Consultas SQL sobre las bases de WhatsApp |
| Pillow | 12.3.0 | Lectura de metadatos EXIF |
| `xxd` | (consignar) | Inspección hexadecimal |
| `hash_lote.py` | propio | Verificación de hashes contra el acta |
| `whatsapp_parser.py` | propio | Extracción de chats de `msgstore.db` y `wa.db` |
| `sqlite_borrados.py` | propio | Búsqueda de texto de registros eliminados |
| `exif_gps.py` | propio | Extracción de fecha, equipo y GPS de fotos |
| `linea_tiempo.py` | propio | Unificación de eventos en una línea de tiempo |

Los scripts propios se adjuntan en el Anexo D, para que otro perito pueda revisarlos y repetir el análisis. Cada resultado obtenido con un script se contrastó con un método independiente (`sha256sum -c`, consultas SQL manuales, inspección hexadecimal).

## 5. Operaciones realizadas

Todas las operaciones se realizaron el 21/11/2026. A continuación se detallan en orden, de forma que otro perito pueda repetirlas.

1. **Copia de trabajo.** Se copió la extracción a una carpeta de trabajo. Todo el análisis posterior se hizo sobre esa copia.
2. **Verificación de integridad.** Se compararon los SHA-256 de los 7 archivos con los del acta, usando `hash_lote.py --verificar` y `sha256sum -c`. Las dos herramientas dieron el mismo resultado: 6 coinciden y 1 no.
3. **Identificación del equipo.** Se leyó `system/build.prop` y se extrajeron marca, modelo, versión de Android, número de serie y zona horaria.
4. **Análisis de WhatsApp.** Se ejecutó `whatsapp_parser.py` sobre `msgstore.db` y `wa.db`, que generó un CSV y un informe HTML. El resultado se verificó con consultas SQL manuales sobre las tablas `message`, `chat`, `jid` y `wa_contacts`. Los timestamps (UTC, en milisegundos) se convirtieron a UTC-3.
5. **Búsqueda de registros eliminados.** Se ejecutó `sqlite_borrados.py` sobre `msgstore.db`. El registro hallado se decodificó manualmente a partir de su estructura en hexadecimal (encabezado de celda SQLite, tipos de columna y valores).
6. **Análisis de imágenes.** Se extrajeron los metadatos EXIF con `exif_gps.py` y se compararon con el nombre de cada archivo. Se inspeccionó visualmente el contenido de cada imagen.
7. **Línea de tiempo.** Se unificaron los eventos de las fuentes anteriores con `linea_tiempo.py`, ordenados por hora argentina.
8. **Verificación final.** Se recalcularon los SHA-256 de `msgstore.db` y `wa.db` después del análisis. Coinciden con los iniciales, lo que confirma que el análisis no modificó la evidencia.

## 6. Resultados

### Punto a) Comunicaciones con la denunciante

Sí existen. En `msgstore.db` hay 9 mensajes (id 1 a 9) con el abonado +5493870001111, agendado como "Carla Compradora", entre el 02/11/2026 a las 18:05 y el 06/11/2026 a las 19:30.

- Tratan sobre la venta de una motocicleta Honda Wave 2022 por $850.000.
- El 03/11 a las 15:30 el abonado informa que transfirió $850.000 (id 6). A las 15:44 el usuario del equipo responde "Recibido" y fija la entrega para el viernes a las 18 en la plaza de Cerrillos (id 7).
- El 06/11 el abonado envía dos mensajes que no tienen respuesta (id 8 y 9). En el último se dirige al usuario del equipo como "Martín".

El nombre de agenda lo carga el usuario del equipo y no acredita identidad. La titularidad de la línea debe requerirse a la empresa de telefonía.

### Punto b) Participación de otra persona

Se constatan 4 mensajes vivos (id 10 a 13) y 1 eliminado (id 16) con el abonado +5493870002222, agendado como "Primo Nacho". Se intercalan con la conversación del punto a):

| Hora | Chat con la denunciante | Chat con +5493870002222 |
| --- | --- | --- |
| 02/11 18:17 | Se le pide el pago total (id 5) | |
| 02/11 18:20 | | "Primo cayó una, quiere la moto" (id 10) |
| 02/11 18:22 | | "que transfiera a la cuenta de siempre" (id 11) |
| 02/11 18:23 | | Mensaje con alias, CVU y titular, **eliminado** (id 16) |
| 03/11 15:44 | Se confirma la recepción del dinero (id 7) | |
| 03/11 15:45 | | "Ya entró la plata, sacala hoy" (id 12) |
| 03/11 16:10 | | "Listo, retirado. Borrá la publicación" (id 13) |

### Punto c) Cuenta de destino del dinero

Dos fuentes independientes indican la misma cuenta:

| Dato | Mensaje eliminado (id 16) | Captura de pantalla |
| --- | --- | --- |
| Alias | SOL.RIO.CAMPO | SOL.RIO.CAMPO |
| CVU | 0000003100099887766554 | — |
| Titular | Rocio Benitez | R. Benitez |
| Monto y fecha | — | $850.000, 03/11/2026 15:29 |

- **Mensaje eliminado.** Se recuperó del espacio no asignado de la página 4 de `msgstore.db` (offset 0x3A1A). Su estructura corresponde a `_id` 16, chat 2 (+5493870002222), mensaje recibido el 02/11/2026 a las 18:23:00. Texto: "Pasale este alias a la mina: SOL.RIO.CAMPO CVU 0000003100099887766554 titular Rocio Benitez". Se puede afirmar que el registro existió, pero no quién lo eliminó ni cuándo.
- **Captura de pantalla.** El archivo `Screenshot_20261103_153112_WhatsApp.jpg` muestra un comprobante de transferencia a SOL.RIO.CAMPO, titular "R. Benitez", operación 000147. El nombre del archivo indica que la captura se tomó el 03/11/2026 a las 15:31:12. En `msgstore.db` no hay mensajes multimedia, de modo que la imagen del comprobante no figura como recibida.

La titularidad efectiva de la cuenta debe requerirse a la entidad emisora del CVU.

### Punto d) Integridad de la evidencia

Seis de los siete archivos coinciden con los hashes del acta y se consideran íntegros. El archivo `IMG_20261106_181502.jpg` no coincide, por lo que fue modificado después del acta del 07/11/2026 a las 10:40.

- Su fecha EXIF (05/11/2026 09:00:00) no es coherente con la que surge del nombre del archivo (06/11/2026 18:15:02).
- Sus coordenadas GPS (-24.8994, -65.4859) corresponden a la zona de Cerrillos.

Por estas razones, los metadatos de ese archivo no se consideran fiables y no se usan para fundar conclusiones. Se pone el hecho en conocimiento de la Fiscalía a los fines que estime corresponder.

## 7. Conclusiones

1. **Punto a)** En el equipo existen comunicaciones por WhatsApp con el abonado +5493870001111, relativas a la venta de una motocicleta por $850.000 y a una transferencia por ese monto.
2. **Punto b)** Existen comunicaciones contemporáneas con el abonado +5493870002222, que hacen referencia a una cuenta para recibir el dinero y a su retiro.
3. **Punto c)** Un mensaje eliminado del chat con +5493870002222 y una captura de pantalla de un comprobante coinciden en el alias SOL.RIO.CAMPO y en la titular "R. Benitez". El mensaje eliminado indica además el CVU 0000003100099887766554.
4. **Punto d)** La evidencia se encuentra íntegra, con excepción del archivo `IMG_20261106_181502.jpg`, que fue modificado después del secuestro y se excluyó de las conclusiones.

Estas conclusiones son de carácter técnico. No se emite opinión sobre la responsabilidad de ninguna persona.

## 8. Anexos

### Anexo A — Hashes SHA-256 completos

```
610f96040606363e63306f78568a978b51908534293d8b06d5f14ea8172af63b  data/data/com.whatsapp/databases/msgstore.db
8e2152df5278c52be1dbbc6db657cb5601d833f3dda32b4a81614e4a0182cb86  data/data/com.whatsapp/databases/wa.db
f56bd0fafe2624b222272d89c30c205de37446a4d30d993d7bc60afecdc4922c  sdcard/DCIM/Camera/IMG_20261101_102233.jpg
dad8e131c8d183dab10c06e96f6f92ba4069b41973cdaeafd952121b2ec3b02b  sdcard/DCIM/Camera/IMG_20261104_130010.jpg
2cea1522889fea9429c8597b80d9a3c09ae338c8653ae446117f94e2adbc3500  sdcard/DCIM/Camera/IMG_20261106_181502.jpg   (según acta)
561b40a15d01d491492a01fd30317542d3f048c5b56c1c2288756cf35c2015a5  sdcard/DCIM/Camera/IMG_20261106_181502.jpg   (calculado en la pericia)
dac8cc31496d73c57c4c032ababd9d4001f0b96b686cf7cfd9b8d7f711dd2f33  sdcard/Pictures/Screenshots/Screenshot_20261103_153112_WhatsApp.jpg
bcbf0b320906dfddf2288973c0b9b8b5eefc1c007e40c60d4102456b38a38c9f  system/build.prop
```

### Anexo B — Línea de tiempo (UTC-3)

| Fecha y hora | Evento | Fuente |
| --- | --- | --- |
| 01/11/2026 10:22:33 | Foto de una motocicleta. GPS: Salta capital, zona centro | IMG_20261101_102233.jpg (EXIF) |
| 02/11/2026 18:05 | La denunciante consulta por la moto publicada en Marketplace | message id 1 |
| 02/11/2026 18:10 | Se ofrece la moto a $850.000 | id 3 |
| 02/11/2026 18:17 | Se pide el pago total y se pacta la entrega el viernes en Cerrillos | id 5 |
| 02/11/2026 18:20 | "Primo cayó una, quiere la moto" | id 10 |
| 02/11/2026 18:22 | "que transfiera a la cuenta de siempre" | id 11 |
| 02/11/2026 18:23 | Mensaje con el alias SOL.RIO.CAMPO, el CVU y la titular (eliminado) | rowid 16, recuperado |
| 03/11/2026 15:29 | Transferencia de $850.000 a SOL.RIO.CAMPO | contenido de la captura |
| 03/11/2026 15:30 | La denunciante informa la transferencia | id 6 |
| 03/11/2026 15:31:12 | Captura del comprobante en WhatsApp | nombre de archivo |
| 03/11/2026 15:44 | Se confirma la recepción y la cita del viernes a las 18 | id 7 |
| 03/11/2026 15:45 | "Ya entró la plata, sacala hoy" | id 12 |
| 03/11/2026 16:10 | "Listo, retirado. Borrá la publicación" | id 13 |
| 06/11/2026 18:15:02 | Foto de una plaza en Cerrillos. Archivo alterado y no fiable (el EXIF indica 05/11 09:00) | IMG_20261106_181502.jpg (nombre) |
| 06/11/2026 18:40 y 19:30 | La denunciante reclama y no obtiene respuesta | id 8 y 9 |
| 07/11/2026 10:40 | Secuestro del equipo y cálculo de hashes | acta |

### Anexo C — Registro eliminado recuperado

Offset 0x3A1A de `msgstore.db`, página 4, en el espacio no asignado entre el arreglo de punteros de celda y el inicio del área de contenido (0x0AA3).

```
81 07 | 10 | 0b | 00 01 08 33 05 05 08 81 45 08 | 02 | 3EB0DELETED00000001 | 01a19e24e320 | 01a19e24eaf0 | Pasale este alias...
largo   rowid hdr  tipos de columna               chat   key_id                timestamp      received       text_data
```

| Campo | Valor |
| --- | --- |
| `_id` | 16 |
| `chat_row_id` | 2 (+5493870002222) |
| `from_me` | 0 (recibido) |
| `timestamp` | 1793654580000 = 02/11/2026 21:23:00 UTC = 18:23:00 UTC-3 |
| `text_data` | 92 caracteres (coincide con el largo declarado en el encabezado) |

### Anexo D — Material adjunto

- Scripts: [`scripts/`](../scripts/) (`hash_lote.py`, `whatsapp_parser.py`, `sqlite_borrados.py`, `exif_gps.py`, `linea_tiempo.py`).
- Salidas: [`resultados/caso1_celular/`](../resultados/caso1_celular/) (`mensajes.csv`, `informe_whatsapp.html`, `fotos.csv`, `linea_tiempo.csv`).
- Imágenes analizadas, con sus hashes: [`evidencia/caso1_celular_android/`](../evidencia/caso1_celular_android/).
