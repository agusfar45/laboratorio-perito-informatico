#!/usr/bin/env python3
"""
adquirir.py - Imagen forense bit a bit de un dispositivo (o archivo), con hash y log.

Hace lo mismo que:
  dd if=/dev/sdX of=pendrive.dd bs=4M conv=noerror,sync      (copia que no se corta con errores)
  dc3dd if=/dev/sdX of=pendrive.dd hash=sha256 log=pendrive.log   (hash y log durante la copia)

  - El origen se abre SOLO en lectura ("rb"). Nunca se escribe en él.
  - SHA-256 y MD5 se calculan mientras se copia (una sola lectura del dispositivo).
  - Si un bloque no se puede leer, se reintenta sector por sector; los sectores ilegibles
    se rellenan con ceros (conv=noerror,sync) y quedan anotados en el log con su número.
    Así la imagen mantiene los offsets correctos y el informe dice qué se perdió.
  - Al terminar, se vuelve a hashear la imagen escrita y se compara (verificación).
  - No pisa una imagen existente.

Uso:
  Linux   (como root):          python3 adquirir.py /dev/sdb pendrive.dd
  Windows (consola de Admin.):  python adquirir.py \\\\.\\PhysicalDrive2 pendrive.dd --tamano 8004304896
  Práctica con un archivo:      python adquirir.py ../evidencia/caso2_pendrive.dd copia.dd

  --simular-errores 100,101   finge que esos sectores están dañados (para practicar noerror,sync)

ANTES de adquirir: identificar bien el dispositivo (lsblk / Get-Disk), conectarlo detrás de
un bloqueador de escritura por hardware y fotografiar el estado del pendrive y sus rótulos.
"""
import argparse
import hashlib
import os
import platform
import sys
import time
from datetime import datetime, timezone

SECTOR = 512


class Lector:
    """Lee el origen por offsets. Permite simular sectores dañados para practicar."""

    def __init__(self, ruta, sectores_malos=()):
        self.f = open(ruta, "rb", buffering=0)  # solo lectura y sin buffer: lo que pedimos es lo que se lee
        self.malos = set(sectores_malos)

    def leer(self, offset, n):
        primero, ultimo = offset // SECTOR, (offset + n - 1) // SECTOR
        if any(s in self.malos for s in range(primero, ultimo + 1)):
            raise OSError(5, "error de E/S (simulado)")
        self.f.seek(offset)
        return self.f.read(n)

    def cerrar(self):
        self.f.close()


def tamano_origen(ruta, indicado):
    if indicado:
        return indicado
    try:
        with open(ruta, "rb") as f:
            return f.seek(0, os.SEEK_END)  # sirve para archivos y para /dev/sdX en Linux
    except OSError:
        sys.exit("No se pudo averiguar el tamaño del origen: indicalo con --tamano "
                 "(en Windows: Get-Disk | Select Number, Size)")


def adquirir(origen, destino, bloque, tamano, sectores_malos, log):
    lector = Lector(origen, sectores_malos)
    sha, md5 = hashlib.sha256(), hashlib.md5()
    ilegibles = []
    inicio = time.time()
    hechos = 0
    with open(destino, "xb") as out:  # "x": falla si ya existe, nunca pisa una imagen
        while hechos < tamano:
            n = min(bloque, tamano - hechos)
            try:
                datos = lector.leer(hechos, n)
            except OSError:
                # bloque con error: reintentar sector por sector y rellenar con ceros los que fallen
                partes = []
                for off in range(hechos, hechos + n, SECTOR):
                    m = min(SECTOR, hechos + n - off)
                    try:
                        partes.append(lector.leer(off, m))
                    except OSError:
                        ilegibles.append(off // SECTOR)
                        partes.append(b"\0" * m)
                datos = b"".join(partes)
            if len(datos) < n:  # lectura corta: fin del dispositivo antes de lo esperado
                log(f"AVISO: lectura corta en el byte {hechos + len(datos)}, se completa con ceros")
                datos += b"\0" * (n - len(datos))
            out.write(datos)
            sha.update(datos); md5.update(datos)
            hechos += n
            pct = 100 * hechos / tamano
            print(f"\r  {hechos:>14,} / {tamano:,} bytes ({pct:5.1f} %)", end="", flush=True)
    print()
    lector.cerrar()
    return sha.hexdigest(), md5.hexdigest(), ilegibles, time.time() - inicio


def hashear(ruta, bloque):
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with open(ruta, "rb") as f:
        while d := f.read(bloque):
            sha.update(d); md5.update(d)
    return sha.hexdigest(), md5.hexdigest()


def rangos(sectores):
    """[5, 6, 7, 10] -> '5-7, 10'"""
    out, i = [], 0
    while i < len(sectores):
        j = i
        while j + 1 < len(sectores) and sectores[j + 1] == sectores[j] + 1:
            j += 1
        out.append(f"{sectores[i]}" if i == j else f"{sectores[i]}-{sectores[j]}")
        i = j + 1
    return ", ".join(out)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origen", help="dispositivo (/dev/sdb, \\\\.\\PhysicalDrive2) o archivo")
    ap.add_argument("destino", help="imagen a crear (.dd)")
    ap.add_argument("--bloque", type=int, default=4 * 1024 * 1024, help="bytes por lectura (bs=4M)")
    ap.add_argument("--tamano", type=int, help="tamaño del origen en bytes (necesario en Windows con PhysicalDrive)")
    ap.add_argument("--log", help="archivo de log (por defecto DESTINO.log)")
    ap.add_argument("--simular-errores", default="", metavar="S1,S2", help="sectores a tratar como dañados")
    ap.add_argument("--perito", default="(nombre del perito)")
    a = ap.parse_args()

    if a.bloque % SECTOR:
        sys.exit(f"--bloque tiene que ser múltiplo de {SECTOR}")
    if os.path.abspath(a.origen) == os.path.abspath(a.destino):
        sys.exit("El destino no puede ser el origen")
    if os.path.exists(a.destino):
        sys.exit(f"{a.destino} ya existe: no se pisa una imagen")
    malos = [int(s) for s in a.simular_errores.split(",") if s.strip()]
    ruta_log = a.log or f"{a.destino}.log"
    lineas = []

    def log(txt=""):
        print(txt)
        lineas.append(txt)

    tamano = tamano_origen(a.origen, a.tamano)
    ahora = lambda: datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    log("=== Adquisición forense (adquirir.py) ===")
    log(f"Perito:        {a.perito}")
    log(f"Equipo:        {platform.node()} · {platform.system()} {platform.release()} · Python {platform.python_version()}")
    log(f"Origen:        {a.origen}  ({tamano:,} bytes = {tamano // SECTOR:,} sectores de {SECTOR})")
    log(f"Destino:       {a.destino}")
    log(f"Bloque:        {a.bloque:,} bytes · modo noerror,sync")
    if malos:
        log(f"SIMULACIÓN:    sectores tratados como dañados: {rangos(sorted(malos))}")
    log(f"Inicio:        {ahora()}")

    sha, md5, ilegibles, segundos = adquirir(a.origen, a.destino, a.bloque, tamano, malos, log)

    log(f"Fin:           {ahora()}  ({segundos:.1f} s, {tamano / max(segundos, 1e-6) / 1e6:.1f} MB/s)")
    log(f"SHA-256 (adquisición): {sha}")
    log(f"MD5     (adquisición): {md5}")
    if ilegibles:
        log(f"Sectores ilegibles:    {len(ilegibles)} ({rangos(ilegibles)}), rellenados con ceros")
    else:
        log("Sectores ilegibles:    ninguno")

    v_sha, v_md5 = hashear(a.destino, a.bloque)
    ok = (v_sha, v_md5) == (sha, md5)
    log(f"Verificación de la imagen escrita: {'OK, coincide' if ok else 'NO COINCIDE'}")
    if not ilegibles and os.path.isfile(a.origen):
        o_sha, _ = hashear(a.origen, a.bloque)
        log(f"Hash del origen releído:           {'OK, coincide' if o_sha == sha else 'NO COINCIDE'}")
    elif ilegibles:
        log("Nota: el hash corresponde a la IMAGEN, que incluye los ceros de relleno. No es comparable con "
            "un hash del dispositivo; se informa junto con la lista de sectores ilegibles.")

    with open(ruta_log, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    with open(f"{a.destino}.sha256", "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{sha}  {os.path.basename(a.destino)}\n")
    print(f"\nLog: {ruta_log} · Hash: {a.destino}.sha256 (sha256sum -c)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
