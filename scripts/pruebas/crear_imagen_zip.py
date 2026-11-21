"""Genera una imagen de prueba para el soporte ZIP/DOCX/XLSX de carving.py.

Uso (desde scripts/):
  python pruebas/crear_imagen_zip.py prueba_zip.dd
  python carving.py prueba_zip.dd -o rec_zip

La imagen tiene un DOCX, un XLSX con comentario ZIP (EOCD de largo variable) y un
ZIP truncado, entre bytes aleatorios. El script imprime el SHA-256 de los originales
para comprobar que el carving los recupera idénticos."""
import io, os, sys, zipfile

def ooxml(carpeta, archivo, cuerpo):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("_rels/.rels", "<Relationships/>")
        z.writestr(f"{carpeta}/{archivo}", cuerpo)
    return b.getvalue()

docx = ooxml("word", "document.xml", "<w:document>Transferir a SOL.RIO.CAMPO</w:document>" * 20)
b = io.BytesIO()
with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", "<Types/>")
    z.writestr("xl/workbook.xml", "<workbook>cuentas</workbook>" * 30)
    z.comment = b"comentario de prueba para el EOCD"
xlsx = b.getvalue()
b = io.BytesIO()
with zipfile.ZipFile(b, "w") as z:
    z.writestr("notas.txt", "x" * 5000)
truncado = b.getvalue()[:3000]

r = lambda n: os.urandom(n).replace(b"PK", b"pk")
img = r(4096) + docx + r(8192) + xlsx + r(4096) + truncado + r(16384)
open(sys.argv[1], "wb").write(img)
for nombre, d in (("docx", docx), ("xlsx", xlsx)):
    import hashlib; print(nombre, len(d), hashlib.sha256(d).hexdigest()[:16])
