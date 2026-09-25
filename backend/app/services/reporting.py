from __future__ import annotations
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def pdf_report(title: str, lines: list[str]):
    """Backwards-compatible compact report."""
    return investigation_pdf({"title": title, "summary_lines": lines})


def investigation_pdf(data: dict) -> bytes:
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Hero",parent=styles["Title"],fontSize=22,leading=26,alignment=TA_CENTER,spaceAfter=5))
    styles.add(ParagraphStyle(name="Muted",parent=styles["BodyText"],fontSize=8.5,textColor=colors.HexColor("#50645d"),leading=11))
    styles.add(ParagraphStyle(name="Section",parent=styles["Heading2"],fontSize=13,leading=16,textColor=colors.HexColor("#0b6b45"),spaceBefore=10,spaceAfter=6))
    story=[Paragraph(str(data.get("title") or "VanRakshak AI Investigation Report"),styles["Hero"]),
           Paragraph("Satellite-based forest intelligence • source-backed evidence • explainable risk",styles["Muted"]),Spacer(1,7*mm)]

    location=data.get("location") or {}
    if location:
        rows=[["Location",str(location.get("place") or "Selected region")],["Coordinates",f"{location.get('lat','—')}, {location.get('lon','—')}"]]
        story += [Paragraph("Investigation",styles["Section"]), _table(rows)]

    warning=data.get("warning") or {}
    if warning:
        rows=[["Warning level",str(warning.get("level","UNKNOWN"))],["Risk score",str(warning.get("score","—"))],["Evidence coverage",f"{round(float(warning.get('coverage') or 0)*100)}%"],["Method",str(warning.get("method",""))]]
        story += [Paragraph("Explainable warning",styles["Section"]), _table(rows)]
        fac=warning.get("factors") or []
        if fac:
            frows=[["Factor","Contribution","Evidence"]]+[[str(x.get("factor")),str(x.get("contribution")),str(x.get("evidence",""))] for x in fac[:10]]
            story += [Spacer(1,3*mm),_table(frows,header=True)]

    change=data.get("change") or {}
    if change:
        multi=change.get("multispectral") or {}; frag=change.get("fragmentation") or {}
        rows=[
            ["Before scene",str((change.get("before") or {}).get("datetime","—"))],
            ["After scene",str((change.get("after") or {}).get("datetime","—"))],
            ["Candidate loss area",f"{change.get('candidate_area_ha','—')} ha"],
            ["NDVI change",str(change.get("mean_ndvi_change","—"))],
            ["NDMI change",str(multi.get("mean_ndmi_change","—"))],
            ["NBR change",str(multi.get("mean_nbr_change","—"))],
            ["Screening confidence",str(change.get("screening_confidence","—"))],
            ["Cloud masked",f"{round(float(change.get('cloud_masked_fraction') or 0)*100,1)}%"],
        ]
        story += [Paragraph("Satellite change evidence",styles["Section"]),_table(rows)]
        if frag:
            fc=frag.get("change") or {}
            story += [Paragraph("Fragmentation change",styles["Section"]),_table([[k,str(v)] for k,v in fc.items()])]
        story += [Paragraph(str(change.get("warning") or ""),styles["Muted"])]

    carbon=data.get("carbon")
    carbon_reference=data.get("carbon_reference")
    if carbon:
        story += [Paragraph("Location-specific mapped carbon impact",styles["Section"]), _table([[k,str(v)] for k,v in carbon.items() if k!="label"])]
    elif carbon_reference:
        story += [
            Paragraph("Carbon reference context — not a local measurement",styles["Section"]),
            _table([[k,str(v)] for k,v in carbon_reference.items() if k!="label"]),
            Paragraph("This broad reference is kept separate from selected-area carbon impact and must not be presented as a local biomass measurement.",styles["Muted"]),
        ]

    action_plan=data.get("action_plan") or {}
    actions=action_plan.get("actions") or []
    if actions:
        arows=[["Priority","What","Where","How","Expected impact"]]
        for x in actions[:8]:
            arows.append([
                str(x.get("priority") or ""),
                str(x.get("what") or ""),
                str(x.get("where") or ""),
                str(x.get("how") or ""),
                str(x.get("expected_impact") or ""),
            ])
        story += [Paragraph("Recommended response plan",styles["Section"]),_table(arows,header=True)]
        if action_plan.get("expected_outcome"):
            story += [Paragraph(str(action_plan.get("expected_outcome")),styles["Muted"])]

    model_quality=data.get("model_quality") or {}
    if model_quality:
        cd=model_quality.get("change_detection") or {}
        cv=model_quality.get("cross_sensor_validation") or {}
        gt=model_quality.get("ground_truth_classification_metrics") or {}
        qrows=[
            ["Validation evidence","Value"],
            ["Optical valid pixels",str(cd.get("valid_pixels","—"))],
            ["Cloud-masked fraction",str(cd.get("cloud_masked_fraction","—"))],
            ["Screening confidence",str(cd.get("screening_confidence","—"))],
            ["IsolationForest overlap",str(cd.get("isolation_forest_candidate_overlap_fraction","—"))],
            ["Sentinel-1 corroboration",str(cv.get("status","—"))],
            ["Sentinel-1 candidate fraction",str(cv.get("sentinel1_candidate_fraction","—"))],
            ["Ground-truth Precision/Recall/F1/IoU","Not claimed" if not gt.get("available") else "Available"],
        ]
        story += [
            Paragraph("Model quality & validation evidence",styles["Section"]),
            _table(qrows,header=True),
            Paragraph(str(gt.get("note") or model_quality.get("data_integrity_rule") or ""),styles["Muted"]),
        ]

    doctor=data.get("forest_doctor") or {}
    if doctor:
        rows=[["Probable driver hypothesis","Relative support"]]+[[x.get("driver",""),f"{x.get('relative_support_pct','—')}%"] for x in (doctor.get("probable_drivers") or [])]
        story += [Paragraph("AI Forest Doctor",styles["Section"]),_table(rows,header=True),Paragraph(str(doctor.get("warning") or ""),styles["Muted"])]

    chain=(data.get("evidence_chain") or {}).get("items") or []
    if chain:
        story += [PageBreak(),Paragraph("Evidence chain",styles["Section"])]
        erows=[["Class","Source","Evidence"]]+[[x.get("kind",""),x.get("source",""),x.get("statement","")] for x in chain]
        story += [_table(erows,header=True)]

    sources=data.get("sources") or {}
    if sources:
        prows=[["Source","Status","Freshness","Observed / fetched","Notes"]]
        for key,row in sources.items():
            if not isinstance(row,dict):
                continue
            prov=row.get("provenance") or {}
            source=prov.get("source") or str(key)
            status="AVAILABLE" if row.get("ok") is True and row.get("data") is not None else "UNAVAILABLE"
            freshness=prov.get("freshness") or ""
            observed=prov.get("observed_at") or prov.get("fetched_at") or ""
            notes=prov.get("notes") or row.get("error") or ""
            prows.append([str(source),status,str(freshness),str(observed),str(notes)[:220]])
        if len(prows)>1:
            story += [Paragraph("Real data provenance",styles["Section"]),_table(prows,header=True)]
            story += [Paragraph("Data-integrity rule: unavailable providers remain unavailable; no environmental value is fabricated. Derived, forecast and scenario outputs are explicitly labelled.",styles["Muted"])]

    if data.get("summary_lines"):
        story += [Paragraph("Summary",styles["Section"])]
        story += [Paragraph(str(x),styles["BodyText"]) for x in data["summary_lines"]]

    story += [Spacer(1,8*mm),Paragraph("Important: VanRakshak outputs are investigation-support estimates. Satellite/news/road correlations do not establish illegality or legal causation. Field verification remains necessary.",styles["Muted"])]
    doc.build(story); buf.seek(0); return buf.getvalue()


def _table(rows, header=False):
    t=Table(rows,repeatRows=1 if header else 0,colWidths=None,hAlign="LEFT")
    style=[("VALIGN",(0,0),(-1,-1),"TOP"),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#b9c8c2")),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef6f2")),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),("LEADING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]
    if header: style += [("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0b6b45")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
    t.setStyle(TableStyle(style)); return t
