#!/usr/bin/env python3
"""
whatsapp_parser.py - Extrae los chats de una base msgstore.db (WhatsApp Android)
y genera un CSV y un informe HTML con la línea de tiempo.

IMPORTANTE (buena práctica): nunca abras la base original. Trabajá sobre una COPIA
y verificá el hash antes y después. Este script abre la base en modo solo lectura.

Uso:
  python3 whatsapp_parser.py --msgstore RUTA/msgstore.db --wa RUTA/wa.db -o salida/

El esquema es el de las versiones modernas (tablas message, chat, jid).
En versiones viejas la tabla se llamaba `messages` y usaba key_remote_jid / data:
si te toca una así, adaptá la consulta SQL de abajo.
"""
import argparse
import csv
import html
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

ART = timezone(timedelta(hours=-3))  # hora de Argentina (los timestamps se guardan en UTC, en milisegundos)

CONSULTA = """
SELECT m._id, m.chat_row_id, j.raw_string AS jid, m.from_me, m.timestamp, m.received_timestamp,
       m.message_type, m.text_data, m.key_id
FROM message m
JOIN chat c ON c._id = m.chat_row_id
JOIN jid  j ON j._id = c.jid_row_id
ORDER BY m.timestamp
"""


def abrir_ro(ruta: Path):
    # mode=ro + immutable=1 -> SQLite no escribe nada (ni journal ni WAL)
    return sqlite3.connect(f"file:{ruta.resolve().as_posix()}?mode=ro&immutable=1", uri=True)


def contactos(wa_db: Path):
    if not wa_db or not wa_db.exists():
        return {}
    con = abrir_ro(wa_db)
    r = {jid: nombre for jid, nombre in con.execute("SELECT jid, display_name FROM wa_contacts")}
    con.close()
    return r


def fecha(ms):
    return datetime.fromtimestamp(ms / 1000, ART).strftime("%d/%m/%Y %H:%M:%S") if ms else ""


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime "→" ni emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--msgstore", required=True, type=Path)
    ap.add_argument("--wa", type=Path, help="wa.db para resolver nombres de contactos")
    ap.add_argument("-o", "--salida", type=Path, default=Path("salida_whatsapp"))
    a = ap.parse_args()

    nombres = contactos(a.wa)
    con = abrir_ro(a.msgstore)
    filas = []
    for _id, chat, jid, from_me, ts, rts, tipo, texto, key in con.execute(CONSULTA):
        numero = "+" + jid.split("@")[0]
        contacto = nombres.get(jid, numero)
        filas.append({
            "id": _id, "chat": chat, "contacto": contacto, "numero": numero,
            "direccion": "ENVIADO" if from_me else "RECIBIDO",
            "fecha_hora_ART": fecha(ts), "recibido_ART": fecha(rts),
            "tipo": tipo, "texto": texto or "", "key_id": key,
        })
    con.close()

    a.salida.mkdir(parents=True, exist_ok=True)
    with open(a.salida / "mensajes.csv", "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: abre bien en Excel
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()) if filas else ["id"])
        w.writeheader(); w.writerows(filas)

    # Informe HTML agrupado por chat
    por_chat = {}
    for f_ in filas:
        por_chat.setdefault((f_["chat"], f_["contacto"], f_["numero"]), []).append(f_)
    partes = ["<!doctype html><meta charset='utf-8'><title>Informe WhatsApp</title>",
              "<style>body{font-family:sans-serif;max-width:800px;margin:auto;background:#efeae2}"
              ".m{padding:6px 10px;margin:4px 0;border-radius:8px;max-width:75%}"
              ".e{background:#d9fdd3;margin-left:auto}.r{background:#fff}.t{font-size:11px;color:#666}"
              "h2{background:#075e54;color:#fff;padding:8px}</style>",
              f"<h1>Informe de chats</h1><p>Fuente: {html.escape(str(a.msgstore))}<br>"
              f"Total mensajes: {len(filas)} &middot; Chats: {len(por_chat)} &middot; Horario: UTC-3</p>"]
    for (chat, contacto, numero), msgs in por_chat.items():
        partes.append(f"<h2>Chat {chat}: {html.escape(contacto)} ({numero}) — {len(msgs)} mensajes</h2>")
        for m in msgs:
            cls = "e" if m["direccion"] == "ENVIADO" else "r"
            partes.append(f"<div class='m {cls}'>{html.escape(m['texto'])}"
                          f"<div class='t'>{m['fecha_hora_ART']} · id {m['id']}</div></div>")
    (a.salida / "informe_whatsapp.html").write_text("\n".join(partes), encoding="utf-8")

    print(f"{len(filas)} mensajes en {len(por_chat)} chats")
    for (chat, contacto, numero), msgs in por_chat.items():
        print(f"  chat {chat}: {contacto:<20} {numero}  {len(msgs)} msgs  "
              f"({msgs[0]['fecha_hora_ART']} → {msgs[-1]['fecha_hora_ART']})")
    # Huecos en los _id: pista de mensajes borrados
    ids = sorted(f_["id"] for f_ in filas)
    huecos = sorted(set(range(ids[0], ids[-1] + 1)) - set(ids)) if ids else []
    sig = ids[-1] + 1 if ids else 1
    print(f"\nIDs faltantes en la secuencia: {huecos or 'ninguno'}  (próximo id esperado: {sig})")
    print("Ojo: si se borró el último mensaje no queda hueco. Por eso hay que revisar el espacio libre con sqlite_borrados.py")
    print(f"\nGenerado: {a.salida/'mensajes.csv'} y {a.salida/'informe_whatsapp.html'}")


if __name__ == "__main__":
    main()
