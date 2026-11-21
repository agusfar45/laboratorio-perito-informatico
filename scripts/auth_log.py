#!/usr/bin/env python3
"""
auth_log.py - Analiza /var/log/auth.log (Debian/Ubuntu) para detectar intrusiones por SSH.

Detecta:
  - fuerza bruta: intentos fallidos por IP (Failed password / Invalid user)
  - accesos exitosos y si vinieron de una IP que antes falló (señal fuerte de intrusión)
  - comandos ejecutados con sudo (qué hizo el intruso)
  - línea de tiempo resumida

Uso:
  python3 auth_log.py auth.log [--umbral 10]
En CentOS/RHEL el archivo equivalente es /var/log/secure.
En sistemas con systemd también: journalctl -u ssh --since "2026-11-14" > ssh.log
"""
import argparse
import re
from collections import Counter, defaultdict

FALLO = re.compile(r"(?:Failed password for (?:invalid user )?(\S+)|Invalid user (\S+)) from (\d+\.\d+\.\d+\.\d+)")
EXITO = re.compile(r"Accepted (\S+) for (\S+) from (\d+\.\d+\.\d+\.\d+) port (\d+)")
SUDO = re.compile(r"sudo:\s+(\S+) : .*?USER=(\S+) ; COMMAND=(.*)")


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime "→" ni emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log")
    ap.add_argument("--umbral", type=int, default=10, help="fallos por IP para considerar fuerza bruta")
    a = ap.parse_args()

    fallos = Counter()
    usuarios_probados = defaultdict(Counter)
    primero, ultimo = {}, {}
    exitos, sudos = [], []

    with open(a.log, encoding="utf-8", errors="replace") as f:
        for linea in f:
            ts = linea[:15]
            if m := FALLO.search(linea):
                usuario = m.group(1) or m.group(2)
                ip = m.group(3)
                fallos[ip] += 1
                usuarios_probados[ip][usuario] += 1
                primero.setdefault(ip, ts); ultimo[ip] = ts
            elif m := EXITO.search(linea):
                metodo, usuario, ip, puerto = m.groups()
                exitos.append((ts, usuario, ip, metodo, puerto))
            elif m := SUDO.search(linea):
                sudos.append((ts, *m.groups()))

    print("=== IPs con intentos fallidos ===")
    for ip, n in fallos.most_common():
        marca = "  <-- FUERZA BRUTA" if n >= a.umbral else ""
        top = ", ".join(u for u, _ in usuarios_probados[ip].most_common(4))
        print(f"{ip:<16} {n:>5} fallos  [{primero[ip]} → {ultimo[ip]}]  usuarios: {top}{marca}")

    print("\n=== Accesos exitosos ===")
    for ts, usuario, ip, metodo, puerto in exitos:
        alerta = f"  <-- ¡¡ÉXITO TRAS {fallos[ip]} FALLOS!!" if fallos[ip] else ""
        print(f"{ts}  usuario={usuario:<8} ip={ip:<16} método={metodo}{alerta}")

    print("\n=== Comandos con sudo ===")
    for ts, quien, como, cmd in sudos:
        print(f"{ts}  {quien} (como {como}): {cmd}")

    sospechosas = {ip for _, _, ip, _, _ in exitos if fallos[ip]}
    print("\n=== Conclusión automática (verificala vos) ===")
    if sospechosas:
        print(f"Probable intrusión desde: {', '.join(sorted(sospechosas))}")
    else:
        print("No hay accesos exitosos desde IPs con fallos previos.")


if __name__ == "__main__":
    main()
