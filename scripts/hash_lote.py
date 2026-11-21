#!/usr/bin/env python3
"""
hash_lote.py - Calcula y verifica hashes de evidencia (cadena de custodia).

Genera un manifiesto en el mismo formato que `sha256sum`, así se puede verificar
también desde Linux con:  sha256sum -c manifiesto.txt

Uso:
  python3 hash_lote.py CARPETA_O_ARCHIVO [-o manifiesto.txt] [--md5]
  python3 hash_lote.py CARPETA --verificar manifiesto.txt [--md5]

Con --md5 al generar se escribe además manifiesto.txt.md5 (formato md5sum).
Al verificar, el algoritmo se detecta por el largo de cada hash (32 = MD5,
40 = SHA-1, 64 = SHA-256): sirven actas hechas con md5sum, sha256sum o mezcladas.
Con --verificar ... --md5 se calcula además el MD5 de cada archivo y se muestra,
útil cuando el juzgado pide los dos valores.

Ejemplos:
  python3 hash_lote.py ../evidencia/caso1_celular_android -o mis_hashes.txt --md5
  python3 hash_lote.py ../evidencia/caso1_celular_android --verificar ../evidencia/caso1_acta_secuestro_hashes.txt
  python3 hash_lote.py ../evidencia/caso1_celular_android --verificar mis_hashes.txt.md5
"""
import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

BLOQUE = 1024 * 1024  # leer de a 1 MB: sirve para imágenes de disco de cientos de GB
POR_LARGO = {32: "md5", 40: "sha1", 64: "sha256"}


def hashear(ruta: Path, algoritmos=("sha256",)):
    """Una sola lectura del archivo alimenta todos los algoritmos a la vez."""
    hs = {a: hashlib.new(a) for a in algoritmos}
    with open(ruta, "rb") as f:
        while bloque := f.read(BLOQUE):
            for h in hs.values():
                h.update(bloque)
    return {a: h.hexdigest() for a, h in hs.items()}


def listar(base: Path):
    if base.is_file():
        return [base]
    return sorted(p for p in base.rglob("*") if p.is_file())


def nombre_relativo(p: Path, base: Path):
    return p.name if base.is_file() else p.relative_to(base).as_posix()


def escribir_lf(ruta, lineas):
    # Siempre LF: en Windows write_text pondría CRLF y `sha256sum -c` de Linux
    # fallaría buscando "archivo\r".
    Path(ruta).write_bytes(("\n".join(lineas) + "\n").encode("utf-8"))


def generar(base: Path, salida, md5: bool):
    algos = ("sha256", "md5") if md5 else ("sha256",)
    cabecera = f"# Manifiesto generado {datetime.now().isoformat(timespec='seconds')} sobre {base.resolve()}"
    lineas = {a: [cabecera] for a in algos}
    for p in listar(base):
        r = hashear(p, algos)
        rel = nombre_relativo(p, base)
        for alg in algos:
            lineas[alg].append(f"{r[alg]}  {rel}")
        extra = f"  md5={r['md5']}" if md5 else ""
        print(f"{r['sha256']}  {p.stat().st_size:>12} B  {rel}{extra}")
    if salida:
        escribir_lf(salida, lineas["sha256"])
        print(f"\nManifiesto SHA-256 guardado en {salida}  (sha256sum -c {salida})")
        if md5:
            escribir_lf(f"{salida}.md5", lineas["md5"])
            print(f"Manifiesto MD5     guardado en {salida}.md5  (md5sum -c {salida}.md5)")


def leer_manifiesto(manifiesto: Path):
    """Devuelve {ruta_relativa: {algoritmo: hash}}."""
    esperados = {}
    for n, linea in enumerate(manifiesto.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip() or linea.startswith("#"):
            continue
        h, rel = linea.split(maxsplit=1)
        alg = POR_LARGO.get(len(h))
        if alg is None:
            sys.exit(f"{manifiesto}:{n}: hash de {len(h)} caracteres, no es MD5 / SHA-1 / SHA-256")
        esperados.setdefault(rel.strip().lstrip("*"), {})[alg] = h.lower()
    return esperados


def verificar(base: Path, manifiesto: Path, md5: bool = False):
    esperados = leer_manifiesto(manifiesto)
    usados = sorted({alg for hs in esperados.values() for alg in hs})
    print(f"Manifiesto: {manifiesto}  (algoritmo: {', '.join(usados)})\n")

    actuales = {nombre_relativo(p, base): p for p in listar(base)}
    ok = mal = falta = 0
    for rel, hs in esperados.items():
        if rel not in actuales:
            print(f"[FALTA]     {rel}"); falta += 1; continue
        algos = tuple(sorted(set(hs) | ({"md5"} if md5 else set())))
        reales = hashear(actuales[rel], algos)
        distintos = [alg for alg in hs if reales[alg] != hs[alg]]
        extra = [f"            {alg} calculado {reales[alg]}" for alg in algos if alg not in hs]
        if not distintos:
            print(f"[OK]        {rel}  ({'+'.join(sorted(hs))})"); ok += 1
        else:
            print(f"[ALTERADO]  {rel}"); mal += 1
            for alg in distintos:
                print(f"            {alg} esperado  {hs[alg]}")
                print(f"            {alg} actual    {reales[alg]}")
        for e in extra:
            print(e)
    nuevos = sorted(set(actuales) - set(esperados))
    for rel in nuevos:
        print(f"[NUEVO]     {rel}  (no figuraba en el acta)")

    print(f"\nResumen: {ok} OK, {mal} alterados, {falta} faltantes, {len(nuevos)} nuevos")
    return 0 if (mal == falta == len(nuevos) == 0) else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime "→" ni emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ruta", type=Path)
    ap.add_argument("-o", "--salida")
    ap.add_argument("--md5", action="store_true", help="calcular también MD5 (lo piden algunos juzgados)")
    ap.add_argument("--verificar", type=Path, metavar="MANIFIESTO")
    a = ap.parse_args()
    if not a.ruta.exists():
        sys.exit(f"No existe: {a.ruta}")
    if a.verificar:
        sys.exit(verificar(a.ruta, a.verificar, a.md5))
    generar(a.ruta, a.salida, a.md5)


if __name__ == "__main__":
    main()
