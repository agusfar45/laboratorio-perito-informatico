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

## Pendiente

- Comparar con `foremost`, `binwalk` y The Sleuth Kit (`mmls`, `fls`) en Linux.
- Adquisición real: `dc3dd if=/dev/sdX of=pendrive.dd hash=sha256 log=pendrive.log` detrás de un bloqueador de escritura.
