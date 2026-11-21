#!/usr/bin/env python3
"""
sqlite_borrados.py - Busca texto de registros BORRADOS en una base SQLite.

Cuando una app borra un registro, SQLite normalmente no pisa los bytes: marca ese
espacio como libre (freeblocks / páginas libres). Hasta que se reutiliza o se hace
VACUUM, el texto sigue en el archivo. Este script:
  1. Lee todos los textos "vivos" de todas las tablas (consulta normal, solo lectura).
  2. Recorre el archivo crudo byte a byte buscando cadenas de texto UTF-8.
  3. Muestra las cadenas que están en el archivo pero NO en los datos vivos.

Uso:
  python3 sqlite_borrados.py RUTA/msgstore.db [--min 12]

Limitaciones (decilo en el informe): recupera texto, no siempre el registro completo
(fecha, remitente). Para eso hay herramientas que parsean los freeblocks
(p. ej. "undark", "sqlite-deleted-records-parser") o suites comerciales.
También revisá si existen archivos -wal y -journal junto a la base: suelen tener más datos.
"""
import argparse
import re
import sqlite3
import struct
from pathlib import Path

PATRON = re.compile(rb"(?:[\x20-\x7e]|[\xc2-\xf4][\x80-\xbf]{1,3}){%d,}")


def textos_vivos(ruta: Path):
    con = sqlite3.connect(f"file:{ruta.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    vivos = set()
    tablas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tablas:
        for fila in con.execute(f'SELECT * FROM "{t}"'):
            for v in fila:
                if isinstance(v, str):
                    vivos.add(v)
    esquema = {r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")}
    con.close()
    return vivos, esquema, tablas


def es_esquema(s, esquema, tablas):
    """Descarta pedazos de sqlite_master (definiciones de tablas), que no son datos borrados."""
    if re.match(r"^.?(table|index)(\w+)\2", s):
        return True
    baja = [e.lower() for e in esquema]
    sl = s.lower()
    return any(sl[i:i + 12] in e for e in baja for i in range(0, max(1, len(sl) - 11), 6))


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime "→" ni emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db", type=Path)
    ap.add_argument("--min", type=int, default=12, help="largo mínimo de cadena (default 12)")
    a = ap.parse_args()

    crudo = a.db.read_bytes()
    if not crudo.startswith(b"SQLite format 3\x00"):
        raise SystemExit("No parece una base SQLite (falta la firma 'SQLite format 3')")
    tam_pagina = struct.unpack(">H", crudo[16:18])[0] or 65536
    paginas_libres = struct.unpack(">I", crudo[36:40])[0]
    print(f"Base: {a.db}  |  {len(crudo)} bytes  |  página {tam_pagina} B  |  páginas en freelist: {paginas_libres}")
    for ext in ("-wal", "-journal", "-shm"):
        if Path(str(a.db) + ext).exists():
            print(f"  ¡Atención! existe {a.db.name}{ext}: analizalo también")

    vivos, esquema, tablas = textos_vivos(a.db)
    print(f"Tablas: {', '.join(tablas)}  |  textos vivos: {len(vivos)}\n")

    patron = re.compile(PATRON.pattern % a.min)
    hallazgos = 0
    for m in patron.finditer(crudo):
        try:
            s = m.group().decode("utf-8")
        except UnicodeDecodeError:
            continue
        # descartar lo que es dato vivo, parte de un dato vivo o del esquema
        if any(s in v or v in s for v in vivos if len(v) >= a.min) or es_esquema(s, esquema, tablas):
            continue
        if s.startswith("SQLite format"):
            continue
        hallazgos += 1
        pag = m.start() // tam_pagina + 1
        print(f"[offset 0x{m.start():06X} | página {pag}] {s}")
    print(f"\n{hallazgos} cadena(s) no presentes en los datos vivos")


if __name__ == "__main__":
    main()
