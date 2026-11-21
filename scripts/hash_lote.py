#!/usr/bin/env python3
"""
hash_lote.py - Calcula y verifica hashes de evidencia (cadena de custodia).

Genera un manifiesto en el mismo formato que `sha256sum`, así se puede verificar
también desde Linux con:  sha256sum -c manifiesto.txt

Uso:
  python3 hash_lote.py CARPETA_O_ARCHIVO [-o manifiesto.txt] [--md5]
  python3 hash_lote.py CARPETA --verificar manifiesto.txt

Ejemplos:
  python3 hash_lote.py ../evidencia/caso1_celular_android -o mis_hashes.txt
  python3 hash_lote.py ../evidencia/caso1_celular_android --verificar ../evidencia/caso1_acta_secuestro_hashes.txt
"""
import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

BLOQUE = 1024 * 1024  # leer de a 1 MB: sirve para imágenes de disco de cientos de GB


def hashear(ruta: Path, algoritmos=("sha256",)):
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


def generar(base: Path, salida, md5: bool):
    algos = ("sha256", "md5") if md5 else ("sha256",)
    lineas = [f"# Manifiesto generado {datetime.now().isoformat(timespec='seconds')} sobre {base.resolve()}"]
    for p in listar(base):
        r = hashear(p, algos)
        rel = nombre_relativo(p, base)
        lineas.append(f"{r['sha256']}  {rel}")
        extra = f"  md5={r['md5']}" if md5 else ""
        print(f"{r['sha256']}  {p.stat().st_size:>12} B  {rel}{extra}")
    if salida:
        Path(salida).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(f"\nManifiesto guardado en {salida}")


def verificar(base: Path, manifiesto: Path):
    esperados = {}
    for linea in manifiesto.read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.startswith("#"):
            continue
        h, rel = linea.split(maxsplit=1)
        esperados[rel.strip().lstrip("*")] = h.lower()

    actuales = {nombre_relativo(p, base): p for p in listar(base)}
    ok = mal = falta = 0
    for rel, h in esperados.items():
        if rel not in actuales:
            print(f"[FALTA]     {rel}"); falta += 1; continue
        real = hashear(actuales[rel])["sha256"]
        if real == h:
            print(f"[OK]        {rel}"); ok += 1
        else:
            print(f"[ALTERADO]  {rel}\n            esperado {h}\n            actual   {real}"); mal += 1
    nuevos = sorted(set(actuales) - set(esperados))
    for rel in nuevos:
        print(f"[NUEVO]     {rel}  (no figuraba en el acta)")

    print(f"\nResumen: {ok} OK, {mal} alterados, {falta} faltantes, {len(nuevos)} nuevos")
    return 0 if (mal == falta == len(nuevos) == 0) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ruta", type=Path)
    ap.add_argument("-o", "--salida")
    ap.add_argument("--md5", action="store_true", help="calcular también MD5 (lo piden algunos juzgados)")
    ap.add_argument("--verificar", type=Path, metavar="MANIFIESTO")
    a = ap.parse_args()
    if not a.ruta.exists():
        sys.exit(f"No existe: {a.ruta}")
    if a.verificar:
        sys.exit(verificar(a.ruta, a.verificar))
    generar(a.ruta, a.salida, a.md5)


if __name__ == "__main__":
    main()
