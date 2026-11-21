"""Genera un "disquete" FAT12 de 1,44 MB con un archivo normal y uno BORRADO, para probar
sleuthkit_info.py (fls) y ver cómo queda un archivo borrado en FAT.

Uso (desde scripts/):
  python pruebas/crear_fat12.py fat12.dd
  python sleuthkit_info.py fat12.dd

Al borrar en FAT, el sistema solo cambia el primer byte del nombre por 0xE5 y libera
los clusters en la FAT: el contenido sigue en el disco hasta que se sobrescriba.
"""
import struct
import sys

SECTOR, TOTAL, RESERVADOS, NFATS, SEC_FAT, ENTRADAS_RAIZ = 512, 2880, 1, 2, 9, 224
RAIZ = RESERVADOS + NFATS * SEC_FAT                  # sector 19
DATOS = RAIZ + ENTRADAS_RAIZ * 32 // SECTOR          # sector 33 = cluster 2

img = bytearray(TOTAL * SECTOR)

# Sector de arranque (BPB)
bpb = struct.pack("<3s8sHBHBHHBHHHIIBBBI11s8s", b"\xEB\x3C\x90", b"MSDOS5.0", SECTOR, 1, RESERVADOS,
                  NFATS, ENTRADAS_RAIZ, TOTAL, 0xF0, SEC_FAT, 18, 2, 0, 0, 0, 0, 0x29, 0x20261121,
                  b"PRUEBA     ", b"FAT12   ")
img[0:len(bpb)] = bpb
img[510:512] = b"\x55\xAA"

fat = bytearray(SEC_FAT * SECTOR)


def poner_fat(cluster, valor):
    """FAT12: cada entrada ocupa 12 bits, dos entradas comparten 3 bytes."""
    i = cluster * 3 // 2
    actual = struct.unpack_from("<H", fat, i)[0]
    nuevo = (actual & 0x000F) | (valor << 4) if cluster & 1 else (actual & 0xF000) | valor
    struct.pack_into("<H", fat, i, nuevo)


poner_fat(0, 0xFF0); poner_fat(1, 0xFFF)


def entrada(nombre83, cluster, tamano, borrado=False):
    n = bytearray(nombre83.encode("ascii"))
    if borrado:
        n[0] = 0xE5  # así marca FAT un archivo borrado
    # nombre(11) atrib(1) reservado(10) hora(2) fecha(2) cluster(2) tamaño(4); fecha 21/11/2026 10:30
    fecha = ((2026 - 1980) << 9) | (11 << 5) | 21
    hora = (10 << 11) | (30 << 5)
    return bytes(n) + struct.pack("<B10sHHHI", 0x20, b"\0" * 10, hora, fecha, cluster, tamano)


archivos = [
    ("NOTAS   TXT", b"Lista de compras: pan, leche.\n", False),
    ("CUENTAS TXT", b"SOL.RIO.CAMPO  LUNA.PIEDRA.MAR  NUBE.TREN.SAL\n", True),
]
for i, (nombre, contenido, borrado) in enumerate(archivos):
    cluster = 2 + i
    off = (DATOS + cluster - 2) * SECTOR
    img[off:off + len(contenido)] = contenido
    if not borrado:
        poner_fat(cluster, 0xFFF)  # fin de cadena; el borrado queda en 0 (libre)
    img[RAIZ * SECTOR + 32 * i: RAIZ * SECTOR + 32 * (i + 1)] = entrada(nombre, cluster, len(contenido), borrado)

for k in range(NFATS):
    inicio = (RESERVADOS + k * SEC_FAT) * SECTOR
    img[inicio:inicio + len(fat)] = fat

open(sys.argv[1], "wb").write(img)
print(f"{sys.argv[1]}: FAT12, {len(img):,} bytes, 1 archivo normal y 1 borrado")
