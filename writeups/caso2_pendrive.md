# Caso 2 — Pendrive formateado (file carving)

**Contexto.** En un allanamiento apareció un pendrive "vacío". Se hizo una imagen bit a bit
(`caso2_pendrive.dd`, 4 MB). Objetivo: recuperar su contenido.

## 2.1 Hash de la imagen

| Algoritmo | Valor |
|---|---|
| SHA-256 | `63c861e2003ace70fa229ab77c9ce23c38cce93334d8cc6414dcd60ac8fd9d65` |
| MD5 | `46657dba7a7a7a77fe581a34b89adf71` |

Idéntico antes y después del análisis.

## 2.2 Exploración manual

```bash
xxd -l 96 caso2_pendrive.dd          # sector 0
xxd -s 0x1fe -l 2 caso2_pendrive.dd  # firma de boot 55 AA
grep -obUa "%PDF" caso2_pendrive.dd
xxd -s 0x10000 -l 48 caso2_pendrive.dd
```

- El sector 0 tiene datos aleatorios y **no tiene la firma `55 AA`**: no hay MBR ni boot sector, no se
  puede montar → hay que hacer carving.
- Firmas: JPEG en `0x10000`, `0x200000`, `0x300000`; PNG en `0xA0000`; PDF en `0x150000`.
- `FF D9` (fin de JPEG) aparece decenas de veces al azar: por eso el footer se busca **después** de un header.

> En Git Bash para Windows `grep -P` no soporta binario; usé WSL / Python para la misma búsqueda.

## 2.3 Carving

```bash
python carving.py caso2_pendrive.dd -o recuperados
```

→ [salida_carving.txt](../resultados/caso2_pendrive/salida_carving.txt) ·
[recuperados/](../resultados/caso2_pendrive/recuperados/)

| # | Offset | Estado | Contenido |
|---|---|---|---|
| 001 | 0x10000 | completo | Nota "cuentas para cobrar": SOL.RIO.CAMPO, LUNA.PIEDRA.MAR, NUBE.TREN.SAL |
| 002 | 0x200000 | completo | Comprobante $850.000 a SOL.RIO.CAMPO, "R. Benitez", 03/11/2026 15:29 |
| 003 | 0x300000 | **incompleto** | Foto de una moto, sólo la parte superior |
| 004 | 0xA0000 | completo | PNG genérico, sin relevancia |
| 005 | 0x150000 | completo | PDF "RECIBO PRACTICA - moto Honda Wave $850.000" |

**Por qué el 003 está incompleto:** el formateo borra la estructura, no los datos; pero después se
escribió encima de parte de la foto (desde ~`0x301000`). Se perdió el resto, incluido el `FF D9`, y el
script cortó a 64 KB. `003_vista_parcial.png` es una **visualización** generada con Pillow, no evidencia.

## Relación con el Caso 1

- **SOL.RIO.CAMPO** aparece en tres fuentes independientes: mensaje eliminado, captura del celular, pendrive.
- Dos alias más bajo el título "cuentas para cobrar": dato a informar; la Fiscalía decide si investiga.
- **Cuidado con lo que se afirma:** comparé los bytes y el comprobante 002 y la foto 003 **no son los mismos
  archivos** que los del celular (otros hashes y tamaños). Se describen como "de contenido visual coincidente".
  Para comparar por contenido existe el hash perceptual (pHash).

## Limitaciones (van en el informe)

El carving no recupera **nombres ni fechas**: esos datos viven en el sistema de archivos, que no se conserva.

## Extensión: ZIP / DOCX / XLSX

`carving.py` también recupera ZIP y documentos de Office (que son ZIP por dentro). En este pendrive
no había ninguno; lo probé con una [imagen sintética](../scripts/pruebas/crear_imagen_zip.py) →
[salida](../resultados/desafios/salida_carving_zip.txt). Detalle a explicar: un DOCX tiene un
`PK\x03\x04` **por cada archivo interno**, así que después de recuperar uno completo hay que saltarlo
entero para no sacar sus partes como archivos sueltos.

## 2.4 Comparación con herramientas profesionales

La consigna pide `foremost` y `binwalk`, que solo corren en Linux, y en mi PC no hay WSL. Usé dos
equivalentes que existen para Windows y cubren las dos preguntas que importan:

| Pregunta | Herramienta | Comando |
|---|---|---|
| ¿Queda alguna estructura (particiones, sistema de archivos)? | **The Sleuth Kit 4.15** vía `pytsk3` → [sleuthkit_info.py](../scripts/sleuthkit_info.py) (`img_stat` + `mmls` + `fsstat` + `fls -r`) | `python sleuthkit_info.py caso2_pendrive.dd` |
| ¿Un carver profesional recupera lo mismo que el mío? | **PhotoRec 7.3** (CGSecurity), modo batch | `photorec_win /log /d photorec/rec /cmd caso2_pendrive.dd partition_none,fileopt,everything,enable,wholespace,search` |

Siempre sobre una copia; el SHA-256 de la imagen (`63c861e2…9d65`) fue el mismo antes y después.

**Sleuth Kit** → [sleuthkit_info.txt](../resultados/caso2_pendrive/comparacion_herramientas/sleuthkit_info.txt):
ni `mmls` ni `fsstat` reconocen nada. Confirma con una herramienta forense estándar lo que vi a mano
con `xxd` (sector 0 aleatorio, sin `55 AA`): **no hay estructura que listar, corresponde carving**.

Para comprobar que el script sí lista archivos cuando hay sistema de archivos, armé un
[disquete FAT12 de prueba](../scripts/pruebas/crear_fat12.py) con un archivo borrado →
[salida](../resultados/caso2_pendrive/comparacion_herramientas/sleuthkit_fat12_prueba.txt):

```
  *      4          46  /_UENTAS.TXT  -> "SOL.RIO.CAMPO  LUNA.PIEDRA.MAR  NUBE.TREN.SAL."
```

En FAT, borrar solo cambia el primer byte del nombre por `0xE5` y libera los clusters. Por eso
`fls` lo muestra como `_UENTAS.TXT` y el contenido sigue ahí (lo leo por número de inodo, como `icat`).

**PhotoRec** → [photorec.log](../resultados/caso2_pendrive/comparacion_herramientas/photorec.log):

| Offset | Mi `carving.py` | PhotoRec | ¿Iguales? |
|---|---|---|---|
| 0x10000 (sector 128) | 001.jpg, 6.910 B | f0000128.jpg, 6.910 B | **Mismo SHA-256** |
| 0xA0000 (sector 1280) | 004.png, 1.714 B | f0001280.png, 1.714 B | **Mismo SHA-256** |
| 0x150000 (sector 2688) | 005.pdf, 418 B | f0002688.pdf, **419 B** | Difiere 1 byte (ver abajo) |
| 0x200000 (sector 4096) | 002.jpg, 15.493 B | f0004096.jpg, 15.493 B | **Mismo SHA-256** |
| 0x300000 (sector 6144) | 003.jpg, fragmento 64 KB | **descartado** ("jpg: 2/3") | Con `keep_corrupted_file` lo guarda como `b0006144.jpg` (32 KB), idéntico a los primeros 32 KB del mío |

Lo que aprendí comparando:

1. **El PDF difiere en 1 byte:** PhotoRec incluye el salto de línea que sigue a `%%EOF` y mi script
   corta justo después de `%%EOF`. El contenido es el mismo; el hash, no. Por eso, cuando dos peritos
   usan herramientas distintas, **los hashes de archivos recuperados por carving no tienen por qué
   coincidir**, y el informe tiene que decir con qué herramienta y versión se obtuvo cada uno.
2. **Archivos dañados:** PhotoRec valida la estructura del JPEG y por defecto descarta los que no
   decodifican. Para una pericia el fragmento sí importa (muestra la moto), así que hay que saber
   pedírselo (`keep_corrupted_file`; el prefijo `b` del nombre significa *broken*).
3. **Falsos positivos:** PhotoRec probó 789 firmas y rechazó 68 candidatos inválidos (67 "dovecot").
   Mi script, con solo 4 firmas, no tiene ese ruido, pero tampoco reconocería otros formatos.
4. Los nombres de PhotoRec son el **sector** de inicio: 128 × 512 = 65.536 = `0x10000`.

Pendiente para cuando tenga Linux/WSL: `foremost -i caso2_pendrive.dd -o foremost_out` y `binwalk`.
La conclusión debería ser la misma: son carvers por firma, igual que PhotoRec.

## 2.5 Cómo se hace la imagen de verdad

No usé un pendrive físico. Escribí [adquirir.py](../scripts/adquirir.py), que reproduce lo que hacen
`dd conv=noerror,sync` y `dc3dd hash= log=`, y lo probé tomando como "dispositivo" la imagen del caso:

- Abre el origen **solo en lectura** y no pisa una imagen existente (lo probé: sale con error).
- Calcula SHA-256 y MD5 **durante** la copia y al terminar vuelve a hashear la imagen escrita.
- Si un bloque falla, reintenta sector por sector, rellena con ceros los ilegibles y los anota en el
  log: la imagen conserva los offsets y el informe dice qué se perdió.

| Prueba | Resultado |
|---|---|
| [Copia limpia](../resultados/caso2_pendrive/adquisicion/pendrive.dd.log) | Mismo SHA-256 que el original; `sha256sum -c` OK |
| [Sectores 128-130 simulados como dañados](../resultados/caso2_pendrive/adquisicion/pendrive_danado.dd.log) | Imagen del mismo tamaño; solo esos 3 sectores quedan en cero; el log los lista |

La segunda prueba deja una enseñanza: los sectores 128-130 son **el comienzo del JPEG 001** (la nota
"cuentas para cobrar"). Con solo 1,5 KB ilegibles, el carving de esa imagen recupera 4 archivos en vez
de 5 y **pierde justo la evidencia más importante**, porque sin header no hay firma que encontrar.

**Procedimiento con un dispositivo real:**

```bash
# Linux
lsblk -o NAME,SIZE,MODEL,SERIAL           # identificar el pendrive por tamaño, modelo y número de serie
sudo dc3dd if=/dev/sdb of=pendrive.dd hash=sha256 log=pendrive.log
sudo python3 adquirir.py /dev/sdb pendrive.dd          # alternativa con este script
```

```powershell
# Windows (consola de Administrador)
Get-Disk | Select-Object Number, FriendlyName, SerialNumber, Size
python adquirir.py \\.\PhysicalDrive2 pendrive.dd --tamano <Size>
```

1. **Bloqueador de escritura por hardware** entre el pendrive y la PC: Windows y Linux escriben en
   los discos apenas se conectan (montaje automático, metadatos, índices). Sin bloqueador no se puede
   garantizar que el original no cambió.
2. Fotografiar el pendrive, sus rótulos y el precinto antes de abrirlo; anotar marca, modelo, capacidad y serie.
3. Identificar el dispositivo por **número de serie**, no solo por la letra o el nombre: confundir
   `if=` con `of=` en `dd` borra la evidencia.
4. Hashear durante la adquisición, verificar la imagen y trabajar siempre sobre una copia.

> Esta parte es simulada: la lectura de un dispositivo físico (`\\.\PhysicalDriveN`, `/dev/sdX`) no la probé.
