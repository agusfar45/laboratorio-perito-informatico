#!/usr/bin/env python3
"""
linea_tiempo.py - Junta en una sola línea de tiempo (hora de Argentina, UTC-3):
  - los mensajes de WhatsApp   (mensajes.csv de whatsapp_parser.py)
  - las fotos                  (fotos.csv de exif_gps.py)
  - eventos cargados a mano    (eventos_manuales.csv: registros borrados, acta, etc.)

Uso:
  python3 linea_tiempo.py --wa salida_wa/mensajes.csv --fotos fotos.csv \
                          --manual eventos_manuales.csv -o linea_tiempo.csv

Criterios (decilos en el informe):
  - Mensajes: timestamp de la base (UTC, ms) convertido a UTC-3 por whatsapp_parser.py.
  - Fotos: la fecha EXIF no tiene zona horaria; se toma como hora local del equipo
    (persist.sys.timezone = America/Argentina/Salta). Si no hay EXIF se usa la fecha
    del NOMBRE del archivo (IMG_AAAAMMDD_HHMMSS / Screenshot_AAAAMMDD_HHMMSS).
  - Si la fecha EXIF y la del nombre difieren, se marca la fila como DISCREPANCIA
    y se listan las dos: el perito no elige una en silencio.
"""
import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

FMT = "%d/%m/%Y %H:%M:%S"
NOMBRE_FECHA = re.compile(r"(\d{8})_(\d{6})")
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]  # %A sale en inglés en Windows
CAMPOS = ["fecha_hora_ART", "tipo", "fuente", "detalle", "referencia", "fiabilidad"]


def leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fecha_de_nombre(nombre):
    m = NOMBRE_FECHA.search(nombre)
    return datetime.strptime("".join(m.groups()), "%Y%m%d%H%M%S") if m else None


def eventos_whatsapp(ruta):
    for m in leer_csv(ruta):
        flecha = "->" if m["direccion"] == "ENVIADO" else "<-"
        yield {
            "fecha_hora_ART": datetime.strptime(m["fecha_hora_ART"], FMT),
            "tipo": f"WhatsApp {m['direccion'].lower()}",
            "fuente": "msgstore.db",
            "detalle": f"[chat {m['chat']}] {flecha} {m['contacto']} ({m['numero']}): {m['texto']}",
            "referencia": f"message._id={m['id']}",
            "fiabilidad": "íntegro (hash OK)",
        }


def eventos_fotos(ruta, alterados):
    for f in leer_csv(ruta):
        exif = datetime.strptime(f["fecha_original"], "%Y:%m:%d %H:%M:%S") if f.get("fecha_original") else None
        nombre = fecha_de_nombre(f["archivo"])
        lugar = f" GPS {f['lat']},{f['lon']}" if f.get("lat") else " sin GPS"
        fiab = "ALTERADO (hash distinto al acta)" if f["archivo"] in alterados else "íntegro (hash OK)"
        if exif and nombre and abs((exif - nombre).total_seconds()) > 60:
            # Una fila por cada fecha, las dos marcadas: que se vea la contradicción
            for cuando, origen in ((nombre, "según NOMBRE"), (exif, "según EXIF")):
                yield {"fecha_hora_ART": cuando, "tipo": "Foto (DISCREPANCIA)", "fuente": "sdcard",
                       "detalle": f"{f['archivo']} {origen}.{lugar}", "referencia": f["archivo"],
                       "fiabilidad": fiab}
        else:
            yield {"fecha_hora_ART": exif or nombre,
                   "tipo": "Foto" if exif else "Captura (fecha del nombre)",
                   "fuente": "sdcard", "detalle": f"{f['archivo']}.{lugar}", "referencia": f["archivo"],
                   "fiabilidad": fiab}


def eventos_manuales(ruta):
    for e in leer_csv(ruta):
        e = {k: e.get(k, "") for k in CAMPOS}
        e["fecha_hora_ART"] = datetime.strptime(e["fecha_hora_ART"], FMT)
        yield e


def main():
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wa", type=Path, required=True)
    ap.add_argument("--fotos", type=Path)
    ap.add_argument("--manual", type=Path)
    ap.add_argument("--alterados", nargs="*", default=[], help="archivos cuyo hash no coincidió con el acta")
    ap.add_argument("-o", "--salida", type=Path, default=Path("linea_tiempo.csv"))
    a = ap.parse_args()

    ev = list(eventos_whatsapp(a.wa))
    if a.fotos:
        ev += eventos_fotos(a.fotos, set(a.alterados))
    if a.manual:
        ev += eventos_manuales(a.manual)
    ev.sort(key=lambda e: e["fecha_hora_ART"])

    with open(a.salida, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: abre bien en Excel
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for e in ev:
            w.writerow({**e, "fecha_hora_ART": e["fecha_hora_ART"].strftime(FMT)})

    dia = None
    for e in ev:
        d = f"{DIAS[e['fecha_hora_ART'].weekday()]} {e['fecha_hora_ART']:%d/%m/%Y}"
        if d != dia:
            print(f"\n=== {d} ===")
            dia = d
        marca = "  !!" if "ALTERADO" in e["fiabilidad"] or "borrado" in e["fiabilidad"].lower() else ""
        print(f"{e['fecha_hora_ART']:%H:%M:%S}  {e['tipo']:<28} {e['detalle'][:110]}{marca}")
    print(f"\n{len(ev)} eventos -> {a.salida}")


if __name__ == "__main__":
    main()
