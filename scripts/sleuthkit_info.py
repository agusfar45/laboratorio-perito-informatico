#!/usr/bin/env python3
"""
sleuthkit_info.py - Primer vistazo a una imagen con The Sleuth Kit (vía pytsk3).

Equivale a correr, en Linux:
  img_stat imagen.dd    -> tamaño de la imagen
  mmls     imagen.dd    -> tabla de particiones (MBR / GPT)
  fsstat   imagen.dd    -> sistema de archivos (FAT, NTFS, ext4...)
  fls -r   imagen.dd    -> listado de archivos, incluidos los BORRADOS (marcados con *)

Si no hay tabla de particiones ni sistema de archivos (pendrive formateado y
sobrescrito, disco cifrado...), Sleuth Kit no puede listar nada y queda el carving.

Uso:
  pip install pytsk3
  python3 sleuthkit_info.py imagen.dd [--offset SECTOR]
"""
import argparse
import sys

try:
    import pytsk3
except ImportError:
    sys.exit("Falta pytsk3:  pip install pytsk3")


TIPOS_FS = {getattr(pytsk3, n): n[len("TSK_FS_TYPE_"):] for n in dir(pytsk3)
            if n.startswith("TSK_FS_TYPE_") and not n.endswith(("DETECT", "ENUM"))}


def error(ex):
    return str(ex).strip().splitlines()[0]


def vista_previa(entrada, maximo=60):
    """Como `icat`: lee el contenido por número de inodo, aunque el archivo esté borrado."""
    try:
        datos = entrada.read_random(0, min(entrada.info.meta.size, maximo))
    except OSError:
        return ""
    texto = "".join(chr(b) if 32 <= b < 127 else "." for b in datos)
    return f"  -> \"{texto}\""


def listar(directorio, ruta="", nivel=0, limite=200, contador=None):
    contador = contador if contador is not None else [0]
    for entrada in directorio:
        nombre = entrada.info.name.name.decode("utf-8", "replace")
        if nombre in (".", "..") or entrada.info.meta is None:
            continue
        contador[0] += 1
        if contador[0] > limite:
            return
        borrado = "*" if entrada.info.meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC else " "
        es_dir = entrada.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR
        extra = vista_previa(entrada) if borrado == "*" and not es_dir else ""
        print(f"  {borrado} {entrada.info.meta.addr:>6}  {entrada.info.meta.size:>10}  {ruta}/{nombre}{'/' if es_dir else ''}{extra}")
        if es_dir and nivel < 8:
            try:
                listar(entrada.as_directory(), f"{ruta}/{nombre}", nivel + 1, limite, contador)
            except OSError:
                pass


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("imagen")
    ap.add_argument("--offset", type=int, default=None, help="sector de inicio de la partición (si no, se toma de mmls)")
    a = ap.parse_args()

    img = pytsk3.Img_Info(a.imagen)
    print(f"[img_stat] {a.imagen}: {img.get_size():,} bytes  (The Sleuth Kit {pytsk3.TSK_VERSION_STR})\n")

    offsets = []
    print("[mmls] Tabla de particiones")
    try:
        vol = pytsk3.Volume_Info(img)
        print(f"  Tipo: {vol.info.vstype}, tamaño de bloque {vol.info.block_size}")
        for p in vol:
            desc = p.desc.decode("utf-8", "replace")
            print(f"  {p.addr:>3}  inicio {p.start:>10}  largo {p.len:>10}  {desc}")
            if p.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
                offsets.append(p.start * vol.info.block_size)
    except OSError as ex:
        print(f"  No se reconoce tabla de particiones ({error(ex)})")
    if a.offset is not None:
        offsets = [a.offset * 512]
    if not offsets:
        offsets = [0]  # sin tabla: probar el sistema de archivos al principio de la imagen

    encontrados = 0
    for off in offsets:
        print(f"\n[fsstat] Sistema de archivos en el byte {off}")
        try:
            fs = pytsk3.FS_Info(img, offset=off)
        except OSError as ex:
            print(f"  No se reconoce sistema de archivos ({error(ex)})")
            continue
        encontrados += 1
        tipo = TIPOS_FS.get(fs.info.ftype, fs.info.ftype)
        print(f"  Tipo: {tipo}, bloque {fs.info.block_size} B, {fs.info.block_count} bloques")
        print("\n[fls -r] Archivos (* = borrado; los $ son entradas virtuales de Sleuth Kit)")
        listar(fs.open_dir("/"))

    if not encontrados:
        print("\nNo hay sistema de archivos que listar: queda el carving (carving.py / PhotoRec / foremost).")


if __name__ == "__main__":
    main()
