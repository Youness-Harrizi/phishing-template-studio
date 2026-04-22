import json
import re
import zipfile
import io
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils


TOKEN_MAPS = {
    "gophish": {
        "{{first_name}}": "{{.FirstName}}",
        "{{last_name}}": "{{.LastName}}",
        "{{email}}": "{{.Email}}",
        "{{company}}": "{{.From}}",
        "{{link}}": '<a href="{{.URL}}">{{.URL}}</a>',
        "{{tracker}}": "{{.Tracker}}",
        "{{department}}": "{{.Position}}",
    },
    "king_phisher": {
        "{{first_name}}": "{first_name}",
        "{{last_name}}": "{last_name}",
        "{{email}}": "{email}",
        "{{company}}": "{company_name}",
        "{{link}}": "{url}",
        "{{department}}": "{title}",
    },
}


def _apply_token_map(text: str, platform: str) -> str:
    for token, replacement in TOKEN_MAPS.get(platform, {}).items():
        text = text.replace(token, replacement)
    return text


def _audit_comment(ctx: dict) -> str:
    if not ctx:
        return ""
    lines = [
        "<!-- ENGAGEMENT AUDIT TRAIL",
        f"  Engagement : {ctx.get('engagement_name', 'N/A')} (Ref: {ctx.get('reference_id', 'N/A')})",
        f"  Client     : {ctx.get('client_name', 'N/A')}",
        f"  Assessment : {ctx.get('assessment_type', 'N/A')}",
        f"  Authorised : {ctx.get('authorized_by', 'N/A')} on {ctx.get('authorization_date', 'N/A')}",
        f"  Scope      : {ctx.get('scope_notes', 'N/A')}",
        f"  Exported   : {datetime.now(timezone.utc).isoformat()}",
        "-->",
    ]
    return "\n".join(lines) + "\n"


def _audit_plain(ctx: dict) -> str:
    raw = _audit_comment(ctx)
    return raw.replace("<!--", "").replace("-->", "").strip()


def export_gophish(template: dict, ctx: dict) -> str:
    html = _apply_token_map(template.get("body_html", ""), "gophish")
    text = _apply_token_map(template.get("body_text", ""), "gophish")
    subject = _apply_token_map(template.get("subject_line", ""), "gophish")
    html = _audit_comment(ctx) + html
    payload = {
        "name": template["name"],
        "subject": subject,
        "html": html,
        "text": text,
        "attachments": [],
    }
    return json.dumps(payload, indent=2)


def export_eml(template: dict, ctx: dict, sender_name: str, sender_email: str, recipient: str = "test@example.com") -> str:
    msg = MIMEMultipart("alternative")
    msg["From"] = email.utils.formataddr((sender_name, sender_email))
    msg["To"] = recipient
    msg["Subject"] = template.get("subject_line", "")
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=sender_email.split("@")[-1] if "@" in sender_email else "example.com")
    msg["X-Mailer"] = "Phishing Template Studio"

    plain_body = (_audit_plain(ctx) + "\n\n" + template.get("body_text", "")).strip()
    html_body = _audit_comment(ctx) + template.get("body_html", "")

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg.as_string()


def export_raw_html(template: dict, ctx: dict) -> str:
    comment = _audit_comment(ctx)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{template['name']}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;
     max-width:600px;margin:0 auto;padding:20px;color:#222;line-height:1.6;}}
a{{color:#0066cc;}}
</style>
</head>
<body>
{comment}
{template.get('body_html','')}
</body>
</html>"""


def export_plain_text(template: dict, ctx: dict) -> str:
    audit = _audit_plain(ctx)
    return f"Subject: {template.get('subject_line','')}\n\n{audit}\n\n{template.get('body_text','')}".strip()


def export_king_phisher(template: dict, ctx: dict) -> str:
    html = _apply_token_map(template.get("body_html", ""), "king_phisher")
    text = _apply_token_map(template.get("body_text", ""), "king_phisher")
    payload = {
        "name": template["name"],
        "subject": template.get("subject_line", ""),
        "html": _audit_comment(ctx) + html,
        "text": text,
    }
    return json.dumps(payload, indent=2)


def export_evilginx(template: dict, ctx: dict) -> str:
    comment = _audit_comment(ctx)
    html = template.get("body_html", "")
    return f"""{comment}
# Evilginx2 companion email template
# Template: {template['name']}
# Subject : {template.get('subject_line','')}
#
# Paste the HTML body below into your phishlet email configuration.

{html}
"""


def export_pdf(template: dict, ctx: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        )
        import re as _re

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                 leftMargin=20*mm, rightMargin=20*mm,
                                 topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle("title", parent=styles["Title"],
                                      fontSize=16, textColor=colors.HexColor("#1a1a2e"))
        meta_style = ParagraphStyle("meta", parent=styles["Normal"],
                                     fontSize=9, textColor=colors.grey)
        body_style = ParagraphStyle("body", parent=styles["Normal"],
                                     fontSize=11, leading=16, spaceAfter=8)
        section_style = ParagraphStyle("section", parent=styles["Heading2"],
                                        fontSize=12, textColor=colors.HexColor("#16213e"))

        story.append(Paragraph(f"Phishing Template Report: {template['name']}", title_style))
        story.append(Spacer(1, 4*mm))

        if ctx:
            meta_lines = [
                f"Engagement: {ctx.get('engagement_name','N/A')} | Client: {ctx.get('client_name','N/A')}",
                f"Assessment: {ctx.get('assessment_type','N/A')} | Authorised by: {ctx.get('authorized_by','N/A')} on {ctx.get('authorization_date','N/A')}",
                f"Scope: {ctx.get('scope_notes','N/A')}",
                f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            ]
            for line in meta_lines:
                story.append(Paragraph(line, meta_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 4*mm))

        story.append(Paragraph("Subject Line", section_style))
        story.append(Paragraph(template.get("subject_line", ""), body_style))
        story.append(Spacer(1, 4*mm))

        story.append(Paragraph("Email Body (Plain Text)", section_style))
        plain = template.get("body_text", "").replace("\n", "<br/>")
        story.append(Paragraph(plain or "(empty)", body_style))

        doc.build(story)
        return buf.getvalue()
    except ImportError:
        # Fallback: return a minimal valid PDF notice
        return b"%PDF-1.4 % reportlab not installed - install with: pip install reportlab\n"


def export_zip(template: dict, ctx: dict, sender_name: str, sender_email: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("gophish.json", export_gophish(template, ctx))
        zf.writestr("king_phisher.json", export_king_phisher(template, ctx))
        zf.writestr("email.eml", export_eml(template, ctx, sender_name, sender_email))
        zf.writestr("email.html", export_raw_html(template, ctx))
        zf.writestr("email.txt", export_plain_text(template, ctx))
        zf.writestr("evilginx_companion.txt", export_evilginx(template, ctx))
        pdf_bytes = export_pdf(template, ctx)
        zf.writestr("report.pdf", pdf_bytes)
    return buf.getvalue()
