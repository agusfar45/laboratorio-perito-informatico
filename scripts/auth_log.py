#!/usr/bin/env python3
"""
auth_log.py - Analiza /var/log/auth.log (Debian/Ubuntu) para detectar intrusiones por SSH.

Detecta:
  - fuerza bruta: intentos fallidos por IP (Failed password / Invalid user)
  - accesos exitosos y si vinieron de una IP que antes falló (señal fuerte de intrusión)
  - comandos ejecutados con sudo (qué hizo el intruso), marcando los típicos de un ataque
  - línea de tiempo resumida

Uso:
  python3 auth_log.py auth.log [--umbral 10] [--html informe_auth.html]
En CentOS/RHEL el archivo equivalente es /var/log/secure.
En sistemas con systemd también: journalctl -u ssh --since "2026-11-14" > ssh.log
"""
import argparse
import hashlib
import html
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

FALLO = re.compile(r"(?:Failed password for (?:invalid user )?(\S+)|Invalid user (\S+)) from (\d+\.\d+\.\d+\.\d+)")
EXITO = re.compile(r"Accepted (\S+) for (\S+) from (\d+\.\d+\.\d+\.\d+) port (\d+)")
SUDO = re.compile(r"sudo:\s+(\S+) : .*?USER=(\S+) ; COMMAND=(.*)")
DESCONEXION = re.compile(r"session closed for user (\S+)")

# Qué indica cada comando si aparece con sudo (para resaltarlo; lo confirma el perito)
SOSPECHOSOS = {
    "useradd": "persistencia (usuario nuevo)", "adduser": "persistencia (usuario nuevo)",
    "usermod": "persistencia / privilegios", "passwd": "cambio de clave",
    "crontab": "persistencia (tarea programada)", "authorized_keys": "persistencia (clave SSH)",
    "tar": "empaquetado de datos", "zip": "empaquetado de datos",
    "curl": "conexión saliente / exfiltración", "wget": "descarga / exfiltración",
    "scp": "copia remota", "nc": "conexión saliente", "ncat": "conexión saliente",
    "shred": "antiforense (borrado seguro)", "rm": "borrado",
    "history": "antiforense", "chattr": "antiforense",
}


def analizar(ruta):
    r = {"fallos": Counter(), "usuarios": defaultdict(Counter), "primero": {}, "ultimo": {},
         "exitos": [], "sudos": [], "cierres": [], "lineas": 0, "desde": None, "hasta": None}
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for linea in f:
            r["lineas"] += 1
            ts = linea[:15]
            r["desde"] = r["desde"] or ts
            r["hasta"] = ts
            if m := FALLO.search(linea):
                usuario, ip = m.group(1) or m.group(2), m.group(3)
                r["fallos"][ip] += 1
                r["usuarios"][ip][usuario] += 1
                r["primero"].setdefault(ip, ts); r["ultimo"][ip] = ts
            elif m := EXITO.search(linea):
                metodo, usuario, ip, puerto = m.groups()
                r["exitos"].append((ts, usuario, ip, metodo, puerto))
            elif m := SUDO.search(linea):
                r["sudos"].append((ts, *m.groups()))
            elif m := DESCONEXION.search(linea):
                r["cierres"].append((ts, m.group(1)))
    r["sospechosas"] = sorted({ip for _, _, ip, _, _ in r["exitos"] if r["fallos"][ip]})
    return r


def motivo(cmd):
    """Devuelve por qué un comando sudo es llamativo, o '' si no lo es."""
    palabras = re.split(r"[\s/]+", cmd)
    for clave, porque in SOSPECHOSOS.items():
        if clave in palabras or (clave == "authorized_keys" and clave in cmd):
            return porque
    return ""


def imprimir(r, umbral):
    print("=== IPs con intentos fallidos ===")
    for ip, n in r["fallos"].most_common():
        marca = "  <-- FUERZA BRUTA" if n >= umbral else ""
        top = ", ".join(u for u, _ in r["usuarios"][ip].most_common(4))
        print(f"{ip:<16} {n:>5} fallos  [{r['primero'][ip]} → {r['ultimo'][ip]}]  usuarios: {top}{marca}")

    print("\n=== Accesos exitosos ===")
    for ts, usuario, ip, metodo, puerto in r["exitos"]:
        alerta = f"  <-- ¡¡ÉXITO TRAS {r['fallos'][ip]} FALLOS!!" if r["fallos"][ip] else ""
        print(f"{ts}  usuario={usuario:<8} ip={ip:<16} método={metodo}{alerta}")

    print("\n=== Comandos con sudo ===")
    for ts, quien, como, cmd in r["sudos"]:
        print(f"{ts}  {quien} (como {como}): {cmd}")

    print("\n=== Conclusión automática (verificala vos) ===")
    if r["sospechosas"]:
        print(f"Probable intrusión desde: {', '.join(r['sospechosas'])}")
    else:
        print("No hay accesos exitosos desde IPs con fallos previos.")


def informe_html(r, ruta_log, umbral, salida):
    e = lambda x: html.escape(str(x))  # TODO lo que viene del log lo controla el atacante: se escapa siempre
    sha = hashlib.sha256(Path(ruta_log).read_bytes()).hexdigest()
    total = sum(r["fallos"].values())
    maximo = max(r["fallos"].values(), default=1)

    # línea de tiempo: inicio/fin de cada ataque + éxitos + sudo + cierres, en orden de aparición en el log
    eventos = []
    for ip in r["fallos"]:
        eventos.append((r["primero"][ip], "ataque", f"Comienzan los fallos desde {ip}"))
        eventos.append((r["ultimo"][ip], "ataque", f"Último fallo desde {ip} ({r['fallos'][ip]} en total)"))
    for ts, u, ip, met, _ in r["exitos"]:
        cls = "critico" if r["fallos"][ip] else "normal"
        eventos.append((ts, cls, f"Acceso exitoso: {u} desde {ip} ({met})"))
    for ts, quien, como, cmd in r["sudos"]:
        eventos.append((ts, "critico" if motivo(cmd) else "normal", f"sudo ({quien}): {cmd}"))
    for ts, u in r["cierres"]:
        eventos.append((ts, "normal", f"Cierre de sesión de {u}"))
    eventos.sort(key=lambda ev: ev[0])  # mismo día: el formato "Mmm dd HH:MM:SS" ordena bien como texto

    p = [f"""<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe auth.log</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:980px;margin:auto;padding:16px;color:#1d2433;background:#f5f6f8}}
h1{{margin-bottom:4px}} h2{{border-bottom:2px solid #1d2433;padding-bottom:4px;margin-top:32px}}
.meta{{color:#555;font-size:14px}} code{{font-size:13px;word-break:break-all}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:14px}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid #e3e5ea;vertical-align:top}}
th{{background:#eceef2}}
.barra{{background:#c0392b;height:12px;border-radius:2px}}
.critico{{background:#fdecea}} .critico td:first-child{{border-left:4px solid #c0392b}}
.ataque{{background:#fff7e6}} .etq{{font-size:12px;color:#c0392b;font-weight:600}}
.alerta{{background:#c0392b;color:#fff;padding:12px 16px;border-radius:6px}}
.ok{{background:#27ae60;color:#fff;padding:12px 16px;border-radius:6px}}
.tarjetas{{display:flex;gap:12px;flex-wrap:wrap}} .tarjetas div{{background:#fff;padding:10px 14px;border-radius:6px;flex:1;min-width:140px}}
.tarjetas b{{display:block;font-size:24px}}
</style>
<h1>Análisis de auth.log</h1>
<p class="meta">Archivo: <code>{e(ruta_log)}</code><br>SHA-256: <code>{sha}</code><br>
{r['lineas']} líneas · {e(r['desde'])} → {e(r['hasta'])} · Generado {datetime.now():%d/%m/%Y %H:%M}<br>
<b>Ojo:</b> syslog no guarda año ni zona horaria; las horas son las del servidor (confirmar con <code>timedatectl</code>).</p>
<div class="tarjetas"><div><b>{total}</b>intentos fallidos</div><div><b>{len(r['fallos'])}</b>IPs atacantes</div>
<div><b>{len(r['exitos'])}</b>accesos exitosos</div><div><b>{len(r['sudos'])}</b>comandos sudo</div></div>"""]

    if r["sospechosas"]:
        p.append(f"<p class='alerta'><b>Probable intrusión</b> desde {e(', '.join(r['sospechosas']))}: "
                 "acceso exitoso desde una IP con intentos fallidos previos. Conclusión automática, verificar.</p>")
    else:
        p.append("<p class='ok'>No hay accesos exitosos desde IPs con fallos previos.</p>")

    p.append("<h2>Intentos fallidos por IP</h2><table><tr><th>IP</th><th>Fallos</th><th style='width:30%'></th>"
             "<th>Ventana</th><th>Usuarios más probados</th></tr>")
    for ip, n in r["fallos"].most_common():
        top = ", ".join(f"{u} ({c})" for u, c in r["usuarios"][ip].most_common(4))
        etq = " <span class='etq'>FUERZA BRUTA</span>" if n >= umbral else ""
        p.append(f"<tr><td><code>{e(ip)}</code>{etq}</td><td>{n}</td>"
                 f"<td><div class='barra' style='width:{100 * n / maximo:.0f}%'></div></td>"
                 f"<td>{e(r['primero'][ip])} → {e(r['ultimo'][ip])}</td><td>{e(top)}</td></tr>")
    p.append("</table>")

    p.append("<h2>Accesos exitosos</h2><table><tr><th>Hora</th><th>Usuario</th><th>IP</th><th>Método</th><th>Fallos previos de esa IP</th></tr>")
    for ts, u, ip, met, puerto in r["exitos"]:
        cls = " class='critico'" if r["fallos"][ip] else ""
        p.append(f"<tr{cls}><td>{e(ts)}</td><td>{e(u)}</td><td><code>{e(ip)}:{e(puerto)}</code></td>"
                 f"<td>{e(met)}</td><td>{r['fallos'][ip] or '—'}</td></tr>")
    p.append("</table>")

    p.append("<h2>Comandos con sudo</h2><table><tr><th>Hora</th><th>Usuario</th><th>Comando</th><th>Qué puede indicar</th></tr>")
    for ts, quien, como, cmd in r["sudos"]:
        m = motivo(cmd)
        cls = " class='critico'" if m else ""
        p.append(f"<tr{cls}><td>{e(ts)}</td><td>{e(quien)} → {e(como)}</td><td><code>{e(cmd)}</code></td><td>{e(m)}</td></tr>")
    p.append("</table>")

    p.append("<h2>Línea de tiempo</h2><table><tr><th>Hora</th><th>Evento</th></tr>")
    for ts, cls, texto in eventos:
        p.append(f"<tr class='{cls}'><td>{e(ts)}</td><td>{e(texto)}</td></tr>")
    p.append("</table><p class='meta'>Generado con auth_log.py. Las marcas en rojo son indicios para "
             "revisar, no conclusiones: cada una se confirma contra el log original.</p></html>")
    Path(salida).write_text("\n".join(p), encoding="utf-8")
    print(f"\nInforme HTML: {salida}")


def main():
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime "→" ni emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log")
    ap.add_argument("--umbral", type=int, default=10, help="fallos por IP para considerar fuerza bruta")
    ap.add_argument("--html", metavar="SALIDA", help="genera además un informe HTML")
    a = ap.parse_args()

    r = analizar(a.log)
    imprimir(r, a.umbral)
    if a.html:
        informe_html(r, a.log, a.umbral, a.html)


if __name__ == "__main__":
    main()
