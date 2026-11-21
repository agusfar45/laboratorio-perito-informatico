# Enunciado — Laboratorio de práctica Perito Informático

Tres casos simulados con evidencia real para trabajar con tus manos: un **celular Android**
(WhatsApp + fotos), un **pendrive formateado** y un **servidor Linux hackeado**.
Cubren los seis temas del aviso: Seguridad, Redes, Servidores, Linux, Android y Python.

> Todo es **ficticio**: personas, números, cuentas, comprobantes. Las IPs son de rangos
> reservados para documentación (RFC 5737). No uses nada de esto fuera del laboratorio.

## Qué necesitás

- Python 3.8 o más nuevo (`python3 --version`)
- Pillow para el script de fotos: `pip install pillow`
- Ideal: una PC con Linux (Ubuntu, o una distro forense como **CAINE** o **Tsurugi** en una
  máquina virtual). En Windows funciona todo con `python` en lugar de `python3`;
  los comandos Linux de cada caso los podés practicar con WSL.

## Estructura

```
evidencia/                 ← lo que "secuestraste"
  caso1_celular_android/   ← extracción lógica de un Samsung (WhatsApp, fotos, build.prop)
  caso1_acta_secuestro_hashes.txt
  caso2_pendrive.dd        ← imagen cruda de 4 MB de un pendrive formateado
  caso3_servidor/auth.log  ← log de SSH de un servidor de un estudio contable
scripts/                   ← tus herramientas en Python
```

## Reglas de oro (te las van a preguntar en la entrevista)

1. **Nunca trabajes sobre el original.** Hacé una copia y trabajá sobre la copia.
2. **Hash antes y después.** El SHA-256 demuestra que la evidencia no cambió.
3. **Documentá todo:** qué hiciste, con qué herramienta y versión, y a qué hora.
4. **Horario:** los sistemas guardan la hora en UTC. Salta está en UTC-3: convertí siempre.
5. **Sos imparcial:** informás lo que encontrás, favorezca o no a alguien.

Antes de arrancar: `cp -a evidencia trabajo` (`-a` conserva las fechas) y hacé todo sobre `trabajo/`.

---

## Caso 1 — Estafa por venta de moto (Android + Seguridad + Python)

**Contexto.** Una vecina de Salta denuncia que pagó $850.000 por una moto que vio en
Marketplace y nunca se la entregaron. Se secuestró el celular del sospechoso. El oficial
calculó los hashes en el lugar del hecho (`caso1_acta_secuestro_hashes.txt`).
Los puntos de pericia que pide la fiscalía son:
a) ¿Hay comunicaciones con la denunciante? b) ¿Participó otra persona?
c) ¿A qué cuenta se mandó el dinero? d) ¿La evidencia está íntegra?

**1.1 — Cadena de custodia.** Verificá la integridad contra el acta:
```bash
cd scripts
python3 hash_lote.py ../trabajo/caso1_celular_android --verificar ../trabajo/caso1_acta_secuestro_hashes.txt
```
Hacelo también con la herramienta de Linux: `cd ../trabajo/caso1_celular_android && sha256sum -c ../caso1_acta_secuestro_hashes.txt`
→ ¿Qué archivo falla? ¿Qué significa para el caso? ¿Qué escribirías en el informe?

**1.2 — Identificar el equipo.** Leé `system/build.prop`.
→ Marca, modelo, versión de Android, número de serie y zona horaria.
Comando útil: `grep -E "model|release|serial|timezone" build.prop`

**1.3 — Chats de WhatsApp.**
```bash
python3 whatsapp_parser.py \
  --msgstore ../trabajo/caso1_celular_android/data/data/com.whatsapp/databases/msgstore.db \
  --wa ../trabajo/caso1_celular_android/data/data/com.whatsapp/databases/wa.db -o salida_wa
```
Abrí `salida_wa/informe_whatsapp.html` en el navegador.
→ Respondé los puntos a) y b). Anotá el número de cada interlocutor.

Hacelo también "a mano" con SQL, que es lo que te van a pedir que sepas:
```bash
sqlite3 msgstore.db ".tables"
sqlite3 msgstore.db "SELECT _id, chat_row_id, from_me, datetime(timestamp/1000,'unixepoch','-3 hours'), text_data FROM message;"
```

**1.4 — Mensajes borrados.** El parser no muestra ninguna cuenta bancaria... pero el
chat 2 dice "la cuenta de siempre".
```bash
python3 sqlite_borrados.py ../trabajo/caso1_celular_android/data/data/com.whatsapp/databases/msgstore.db
```
Probá también: `strings -n 12 msgstore.db` y `xxd msgstore.db | less`.
→ Respondé el punto c). ¿Por qué el mensaje sigue ahí? ¿A qué chat creés que pertenecía y por qué?

**1.5 — Fotos.**
```bash
python3 exif_gps.py ../trabajo/caso1_celular_android/sdcard --csv fotos.csv
```
Pegá las coordenadas en Google Maps.
→ ¿Dónde se sacó cada foto? Compará la fecha EXIF de `IMG_20261106_181502.jpg` con su
nombre de archivo y con el resultado del ejercicio 1.1. ¿Qué concluís?
→ Mirá la captura de pantalla de la carpeta Screenshots. ¿Coincide con algún mensaje?

**1.6 — Línea de tiempo.** Juntá en una tabla todo lo anterior (mensajes, fotos, borrado)
ordenado por fecha y hora de Argentina. Es la parte más valorada de un informe.

---

## Caso 2 — Pendrive formateado (Linux + Python)

**Contexto.** En el allanamiento apareció un pendrive "vacío". Se hizo una imagen
bit a bit (`caso2_pendrive.dd`). Hay que recuperar lo que tenía.

**2.1 — Hash de la imagen** (siempre lo primero):
```bash
sha256sum caso2_pendrive.dd
python3 hash_lote.py ../trabajo/caso2_pendrive.dd --md5
```

**2.2 — Exploración a mano con Linux.** Buscá las firmas de archivos:
```bash
grep -obUaP "\xff\xd8\xff" caso2_pendrive.dd | head    # inicios de JPEG (offset en DECIMAL: 65536 = 0x10000)
grep -obUa "%PDF" caso2_pendrive.dd                       # inicios de PDF
xxd -s 0x10000 -l 64 caso2_pendrive.dd                    # ver los bytes en ese offset
strings -n 8 caso2_pendrive.dd | less                     # texto legible
```

**2.3 — Carving con tu script:**
```bash
python3 carving.py ../trabajo/caso2_pendrive.dd -o recuperados
```
→ ¿Cuántos archivos salen? ¿Qué contiene cada uno? ¿Por qué uno está INCOMPLETO?
→ ¿Hay relación con el Caso 1?

**2.4 — Compará con herramientas profesionales** (en Linux):
```bash
sudo apt install foremost binwalk sleuthkit
foremost -i caso2_pendrive.dd -o foremost_out
binwalk caso2_pendrive.dd
```
→ ¿Recuperan lo mismo que tu script? Conocer Foremost, PhotoRec y Autopsy/Sleuth Kit es clave.

**2.5 — Cómo se hace la imagen de verdad** (practicalo con un pendrive tuyo):
```bash
lsblk                                     # identificar el dispositivo (¡con cuidado!)
sudo dd if=/dev/sdX of=pendrive.dd bs=4M status=progress conv=noerror,sync
sudo dc3dd if=/dev/sdX of=pendrive.dd hash=sha256 log=pendrive.log   # alternativa forense
```
En la vida real se usa un **bloqueador de escritura** (write blocker) para que la PC no modifique el pendrive.

---

## Caso 3 — Servidor hackeado (Redes + Servidores + Linux + Seguridad)

**Contexto.** Un estudio contable de Salta nota un usuario raro en su servidor Ubuntu.
Te dan el `auth.log`.

**3.1 — Con tu script:**
```bash
python3 auth_log.py ../trabajo/caso3_servidor/auth.log
```

**3.2 — Lo mismo con comandos de Linux** (te los pueden pedir en una prueba):
```bash
grep "Failed password" auth.log | grep -oE "from [0-9.]+" | sort | uniq -c | sort -rn
grep "Accepted" auth.log
grep "sudo:" auth.log | grep COMMAND
grep "203.0.113.77" auth.log | tail -5
```

→ Preguntas: ¿desde qué IP entraron? ¿A qué hora (y en hora argentina)? ¿Con qué usuario?
¿Cómo consiguieron la contraseña? ¿Qué hicieron adentro? ¿Hubo robo de datos? ¿Hacia
dónde? ¿Intentaron borrar huellas? ¿El acceso de las 08:02 es sospechoso?
→ Escribí 4 recomendaciones de seguridad para el estudio.

**3.3 — Extra de redes.** Si tuvieras una captura de tráfico (`.pcap`) de esa noche,
¿qué filtro de Wireshark usarías para ver la subida de datos? (pista: `ip.addr == ...` y `http.request.method`).
Practicá con capturas públicas de malware-traffic-analysis.net.

---

## Bonus — Android real con tu propio celular

Solo con **tu** teléfono. Activá Opciones de desarrollador → Depuración USB.
```bash
sudo apt install adb
adb devices
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell pm list packages | grep whatsapp
adb pull /sdcard/DCIM/Camera ./mis_fotos
```
Después pasá `exif_gps.py` por tus fotos. Investigá la herramienta **ALEAPP** (gratuita,
en Python, analiza extracciones Android) y qué son las extracciones lógica, de sistema
de archivos y física. En los laboratorios se usan Cellebrite, Magnet AXIOM y Oxygen.

## Desafíos de Python (para lucirte en la entrevista)

1. Agregá a `hash_lote.py` la opción de verificar también con MD5.
2. Hacé que `auth_log.py` genere un informe HTML como el de WhatsApp.
3. Agregá a `carving.py` los archivos ZIP/DOCX/XLSX (firma `PK\x03\x04`).
4. Hacé un `linea_tiempo.py` que junte los CSV de WhatsApp y de fotos en un solo CSV ordenado por fecha.
5. Subí tus scripts a GitHub con un README. Es tu mejor carta de presentación.

---

## Plantilla de informe pericial (estructura habitual)

1. **Encabezado:** autos/expediente, fiscalía o juzgado, perito, fecha.
2. **Objeto de la pericia:** los puntos de pericia, copiados textuales.
3. **Elementos recibidos:** descripción de cada uno, precintos, estado, hashes de recepción.
4. **Metodología y herramientas:** qué software y versión usaste y por qué (norma ISO/IEC 27037, IRAM 36100).
5. **Operaciones realizadas:** paso a paso, con fecha y hora, de forma que otro perito pueda repetirlo.
6. **Resultados:** respuesta a cada punto de pericia, con referencias a los anexos.
7. **Conclusiones:** breves, técnicas, sin opinar sobre culpabilidad.
8. **Anexos:** reportes, capturas, tablas, hashes finales.

Ejercicio final: redactá el informe del Caso 1 siguiendo esta estructura.

## Preguntas típicas de entrevista

- ¿Qué es un hash y por qué SHA-256 y no solo MD5?
- ¿Qué es la cadena de custodia? ¿Qué hacés si un hash no coincide?
- Diferencia entre extracción lógica, de sistema de archivos y física en Android.
- ¿Qué harías si te llega un celular encendido? ¿Y bloqueado? (modo avión / bolsa de Faraday, no apagarlo sin evaluar)
- ¿Qué es file carving? ¿Qué es el espacio no asignado?
- ¿Qué dice la Ley 26.388? ¿Qué es el Convenio de Budapest?
- ¿Cómo convertís un timestamp Unix a hora argentina?
