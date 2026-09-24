from __future__ import annotations
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def pdf_report(title: str, lines: list[str]):
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=A4); w,h=A4
    c.setFont("Helvetica-Bold",18); c.drawString(50,h-60,title)
    y=h-95; c.setFont("Helvetica",10)
    for line in lines:
        if y < 60: c.showPage(); c.setFont("Helvetica",10); y=h-60
        c.drawString(50,y,str(line)[:115]); y-=16
    c.save(); buf.seek(0); return buf.getvalue()
