"""
Seed script — populates the Phishing Template Studio with realistic sample data.
Run once:  python seed.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import app as flask_app
import json

flask_app.init_db()
client = flask_app.app.test_client()

def post(url, body):
    r = client.post(url, json=body)
    return json.loads(r.data)

def put(url, body):
    r = client.put(url, json=body)
    return json.loads(r.data)

print("Seeding personas…")

p1 = post("/api/personas", {
    "name": "Finance Manager",
    "job_title": "Finance Manager",
    "department": "Finance",
    "industry": "Financial Services",
    "seniority": "senior",
    "communication_style": "formal",
    "language": "en",
    "locale": "en-US",
    "known_platforms": ["Office 365", "Workday", "DocuSign", "SAP"],
})

p2 = post("/api/personas", {
    "name": "IT Helpdesk Analyst",
    "job_title": "IT Support Analyst",
    "department": "IT",
    "industry": "Technology",
    "seniority": "junior",
    "communication_style": "semi-formal",
    "language": "en",
    "locale": "en-US",
    "known_platforms": ["Office 365", "ServiceNow", "Okta", "Slack", "Jira"],
})

p3 = post("/api/personas", {
    "name": "HR Business Partner",
    "job_title": "HR Business Partner",
    "department": "Human Resources",
    "industry": "Healthcare",
    "seniority": "mid",
    "communication_style": "semi-formal",
    "language": "en",
    "locale": "en-GB",
    "known_platforms": ["Workday", "Office 365", "Teams", "ADP"],
})

p4 = post("/api/personas", {
    "name": "C-Suite Executive",
    "job_title": "Chief Financial Officer",
    "department": "Executive",
    "industry": "Manufacturing",
    "seniority": "executive",
    "communication_style": "formal",
    "language": "en",
    "locale": "en-US",
    "known_platforms": ["Office 365", "Salesforce", "Zoom", "DocuSign"],
})

p5 = post("/api/personas", {
    "name": "Software Engineer",
    "job_title": "Senior Software Engineer",
    "department": "Engineering",
    "industry": "Technology",
    "seniority": "senior",
    "communication_style": "casual",
    "language": "en",
    "locale": "en-US",
    "known_platforms": ["Slack", "Jira", "Confluence", "GitHub", "AWS", "Okta"],
})

p6 = post("/api/personas", {
    "name": "Accounts Payable Clerk",
    "job_title": "Accounts Payable Specialist",
    "department": "Finance",
    "industry": "Retail",
    "seniority": "junior",
    "communication_style": "semi-formal",
    "language": "en",
    "locale": "en-US",
    "known_platforms": ["QuickBooks", "Office 365", "SAP", "DocuSign"],
})

personas = [p1, p2, p3, p4, p5, p6]
print(f"  Created {len(personas)} personas.")

print("Seeding templates…")

ENGAGEMENT_RT = {
    "engagement_name": "Spring 2026 Red Team",
    "reference_id": "RT-2026-001",
    "client_name": "Acme Corporation",
    "assessment_type": "Red Team",
    "authorized_by": "Jane Smith, CISO",
    "authorization_date": "2026-03-01",
    "scope_notes": "All business units, 200 target users, 3-week window. Exclude C-suite PA team.",
}

ENGAGEMENT_PHISH = {
    "engagement_name": "Q1 Phishing Simulation",
    "reference_id": "PS-2026-Q1",
    "client_name": "Globex Industries",
    "assessment_type": "Internal Phishing Simulation",
    "authorized_by": "Mark Davies, IT Director",
    "authorization_date": "2026-01-10",
    "scope_notes": "Finance and HR departments only. 150 users. Awareness training follows.",
}

# ── Template 1: MFA Enrollment (IT/Helpdesk) ─────────────────────────────────
t1 = post("/api/templates", {
    "name": "Office 365 MFA Enrollment — IT Helpdesk",
    "description": "Poses as IT helpdesk requiring mandatory MFA re-enrollment via a spoofed O365 portal.",
    "category": "it_helpdesk",
    "persona_id": p2["id"],
    "subject_line": "Action Required: Complete Your Multi-Factor Authentication Enrollment by Friday",
    "body_html": """<p>Dear {{first_name}},</p>

<p>As part of our ongoing security hardening initiative, all employees are required to re-enroll their Multi-Factor Authentication (MFA) devices in our updated Microsoft Authenticator system.</p>

<p><strong>Your current MFA configuration will be deactivated on Friday, 1 May 2026 at 17:00.</strong> After this time, you will be unable to access Office 365, SharePoint, or any company systems until re-enrollment is complete.</p>

<p>To avoid disruption to your work, please complete the enrollment process now using your company credentials:</p>

<p style="text-align:center;margin:24px 0">
  <a href="{{link}}" style="background:#0078d4;color:#fff;padding:12px 28px;border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
    Enroll My Device Now
  </a>
</p>

<p>This process takes approximately <strong>3 minutes</strong> and requires your current password and a phone or authenticator app.</p>

<p>If you have already completed this step, please disregard this message. If you experience any issues, reply to this email or raise a ticket via ServiceNow (Ref: <strong>{{ticket_number}}</strong>).</p>

<p>Thank you for helping keep {{company}} secure.</p>

<br>
<p>Best regards,<br>
<strong>{{sender_name}}</strong><br>
{{sender_title}}<br>
IT Security &amp; Helpdesk | {{company}}<br>
📧 it-security@{{company}}.com &nbsp;|&nbsp; ☎ ext. 4400</p>""",
    "body_text": """Dear {{first_name}},

As part of our ongoing security hardening initiative, all employees are required to re-enroll their Multi-Factor Authentication (MFA) devices in our updated Microsoft Authenticator system.

Your current MFA configuration will be deactivated on Friday, 1 May 2026 at 17:00. After this time, you will be unable to access Office 365, SharePoint, or any company systems until re-enrollment is complete.

To avoid disruption to your work, please complete the enrollment process now:

  {{link}}

This process takes approximately 3 minutes and requires your current password and a phone or authenticator app.

If you experience any issues, reply to this email or raise a ticket via ServiceNow (Ref: {{ticket_number}}).

Thank you for helping keep {{company}} secure.

Best regards,
{{sender_name}}
{{sender_title}}
IT Security & Helpdesk | {{company}}""",
    "signature_block": "{{sender_name}}\n{{sender_title}}\nIT Security & Helpdesk | {{company}}\nit-security@corp.com | ext. 4400",
    "tags": ["mfa", "o365", "helpdesk", "microsoft", "credential-harvest"],
    "engagement_context": ENGAGEMENT_RT,
})

# ── Template 2: Invoice Approval (Finance) ────────────────────────────────────
t2 = post("/api/templates", {
    "name": "Urgent Invoice Approval — CFO Impersonation",
    "description": "Executive impersonation targeting AP/finance staff to approve a fraudulent wire transfer.",
    "category": "finance_accounting",
    "persona_id": p6["id"],
    "subject_line": "Urgent: Invoice #{{ticket_number}} Requires Your Immediate Approval",
    "body_html": """<p>Hi {{first_name}},</p>

<p>I'm reaching out directly as we have a time-sensitive payment that needs to be processed today before the bank cutoff at 15:00.</p>

<p>We have an outstanding invoice from <strong>TechSupply Partners Ltd</strong> (Invoice <strong>#{{ticket_number}}</strong>) for <strong>$147,500.00</strong> that requires your sign-off. This relates to the Q1 infrastructure procurement we discussed in last week's budget review.</p>

<p>Please review and approve via our secure payment portal:</p>

<p style="text-align:center;margin:24px 0">
  <a href="{{link}}" style="background:#1a5276;color:#fff;padding:12px 28px;border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
    Review &amp; Approve Payment
  </a>
</p>

<p>The vendor has indicated they will apply a <strong>2% late payment penalty</strong> if this is not settled by end of business today. I would handle this myself but I'm in back-to-back board meetings until 18:00.</p>

<p>Please confirm by reply once completed. Do not discuss this with other team members as it is commercially sensitive.</p>

<p>Thank you,<br>
<strong>{{sender_name}}</strong><br>
{{sender_title}}<br>
{{company}}</p>

<p style="font-size:11px;color:#999">Sent from my iPhone</p>""",
    "body_text": """Hi {{first_name}},

I'm reaching out directly as we have a time-sensitive payment that needs to be processed today before the bank cutoff at 15:00.

We have an outstanding invoice from TechSupply Partners Ltd (Invoice #{{ticket_number}}) for $147,500.00 that requires your sign-off.

Please review and approve via our secure payment portal:

  {{link}}

The vendor will apply a 2% late payment penalty if not settled by end of business today. I'm in back-to-back board meetings until 18:00 so please handle this.

Please confirm by reply once completed. Do not discuss this with other team members as it is commercially sensitive.

Thank you,
{{sender_name}}
{{sender_title}}
{{company}}

Sent from my iPhone""",
    "signature_block": "{{sender_name}}\n{{sender_title}}\n{{company}}",
    "tags": ["bec", "wire-fraud", "invoice", "executive-impersonation", "finance"],
    "engagement_context": ENGAGEMENT_RT,
})

# ── Template 3: Payslip / HR Payroll ─────────────────────────────────────────
t3 = post("/api/templates", {
    "name": "Payslip Available — HR Workday Portal",
    "description": "HR impersonation luring employees to a fake Workday portal to harvest credentials.",
    "category": "hr_payroll",
    "persona_id": p3["id"],
    "subject_line": "Your Payslip for {{deadline}} Is Now Available",
    "body_html": """<p>Dear {{first_name}},</p>

<p>Your payslip for the period ending <strong>{{deadline}}</strong> is now available to view and download via the <strong>Workday HR Portal</strong>.</p>

<p>Additionally, as part of our annual benefits review, all employees are required to confirm their <strong>direct deposit banking details</strong> and emergency contact information by <strong>Friday, 1 May 2026</strong>.</p>

<p>Employees who do not confirm their details by the deadline may experience a delay in their next payroll cycle.</p>

<p style="text-align:center;margin:24px 0">
  <a href="{{link}}" style="background:#e84d4d;color:#fff;padding:12px 28px;border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
    View My Payslip &amp; Confirm Details
  </a>
</p>

<p>If you have any questions about your pay or benefits, please contact the HR team directly.</p>

<br>
<p>Kind regards,<br>
<strong>{{sender_name}}</strong><br>
{{sender_title}}<br>
Human Resources | {{company}}<br>
hr@{{company}}.com</p>""",
    "body_text": """Dear {{first_name}},

Your payslip for the period ending {{deadline}} is now available to view and download via the Workday HR Portal.

Additionally, all employees are required to confirm their direct deposit banking details and emergency contact information by Friday, 1 May 2026. Employees who do not confirm their details by the deadline may experience a delay in their next payroll cycle.

Access your payslip and confirm your details here:

  {{link}}

If you have any questions about your pay or benefits, please contact the HR team directly.

Kind regards,
{{sender_name}}
{{sender_title}}
Human Resources | {{company}}
hr@corp.com""",
    "signature_block": "{{sender_name}}\n{{sender_title}}\nHuman Resources | {{company}}\nhr@corp.com",
    "tags": ["payroll", "workday", "hr", "credential-harvest", "banking-details"],
    "engagement_context": ENGAGEMENT_PHISH,
})

# ── Template 4: Suspicious Login Alert (Security) ────────────────────────────
t4 = post("/api/templates", {
    "name": "Suspicious Sign-In Alert — Account Locked",
    "description": "Spoofed security alert claiming the target's account has been locked due to unusual activity.",
    "category": "security_alert",
    "persona_id": p5["id"],
    "subject_line": "Security Alert: Unusual Sign-In Detected on Your Account — Immediate Action Required",
    "body_html": """<p>Dear {{first_name}},</p>

<p>Our security systems have detected a <strong>suspicious sign-in attempt</strong> on your {{company}} account from an unrecognised device and location:</p>

<table style="border-collapse:collapse;margin:16px 0;font-size:13px">
  <tr style="background:#f5f5f5"><td style="padding:8px 16px;border:1px solid #ddd"><strong>Location</strong></td><td style="padding:8px 16px;border:1px solid #ddd">Kyiv, Ukraine</td></tr>
  <tr><td style="padding:8px 16px;border:1px solid #ddd"><strong>Device</strong></td><td style="padding:8px 16px;border:1px solid #ddd">Windows 11 — Chrome 123</td></tr>
  <tr style="background:#f5f5f5"><td style="padding:8px 16px;border:1px solid #ddd"><strong>Time</strong></td><td style="padding:8px 16px;border:1px solid #ddd">{{deadline}}</td></tr>
  <tr><td style="padding:8px 16px;border:1px solid #ddd"><strong>Status</strong></td><td style="padding:8px 16px;border:1px solid #ddd"><span style="color:#c0392b;font-weight:bold">🔴 Blocked — Account Temporarily Locked</span></td></tr>
</table>

<p>As a precaution, your account has been <strong>temporarily locked</strong>. You must verify your identity to restore access. Failure to verify within <strong>24 hours</strong> will result in a permanent account suspension pending an IT security review.</p>

<p style="text-align:center;margin:24px 0">
  <a href="{{link}}" style="background:#c0392b;color:#fff;padding:12px 28px;border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
    Verify My Identity &amp; Restore Access
  </a>
</p>

<p>If you recognise this sign-in, you may also click the button above to mark it as safe.</p>

<br>
<p>Regards,<br>
<strong>{{sender_name}}</strong><br>
{{sender_title}}<br>
Security Operations Centre | {{company}}<br>
🔒 security@{{company}}.com &nbsp;|&nbsp; Incident Ref: <strong>{{ticket_number}}</strong></p>""",
    "body_text": """Dear {{first_name}},

Our security systems have detected a suspicious sign-in attempt on your {{company}} account from an unrecognised device and location.

  Location : Kyiv, Ukraine
  Device   : Windows 11 — Chrome 123
  Time     : {{deadline}}
  Status   : BLOCKED — Account Temporarily Locked

Your account has been temporarily locked. You must verify your identity to restore access within 24 hours, or your account will be permanently suspended pending an IT security review.

Verify your identity here:

  {{link}}

If you recognise this sign-in, you may use the link above to mark it as safe.

Regards,
{{sender_name}}
{{sender_title}}
Security Operations Centre | {{company}}
security@corp.com | Incident Ref: {{ticket_number}}""",
    "signature_block": "{{sender_name}}\n{{sender_title}}\nSecurity Operations Centre | {{company}}\nsecurity@corp.com",
    "tags": ["security-alert", "account-locked", "okta", "credential-harvest", "fear"],
    "engagement_context": ENGAGEMENT_RT,
})

# ── Template 5: Shared Document (Collaboration) ───────────────────────────────
t5 = post("/api/templates", {
    "name": "Shared Document — SharePoint / OneDrive",
    "description": "Low-friction collaboration lure mimicking a SharePoint document share notification.",
    "category": "collaboration_platform",
    "persona_id": p1["id"],
    "subject_line": "{{sender_name}} has shared a file with you: 'Q1 Budget Review — FINAL.xlsx'",
    "body_html": """<table style="max-width:600px;margin:0 auto;font-family:Segoe UI,Arial,sans-serif;border:1px solid #e0e0e0">
  <tr style="background:#0078d4;padding:16px">
    <td style="padding:16px">
      <span style="color:#fff;font-size:20px;font-weight:700">Microsoft SharePoint</span>
    </td>
  </tr>
  <tr>
    <td style="padding:28px">
      <p style="margin:0 0 8px;font-size:15px"><strong>{{sender_name}}</strong> shared a file with you</p>
      <p style="margin:0 0 20px;color:#555;font-size:13px">{{sender_name}} ({{sender_title}}) has shared the following document and wants you to review it.</p>

      <table style="border:1px solid #ddd;border-radius:4px;padding:16px;width:100%;margin-bottom:20px">
        <tr>
          <td>
            <div style="font-size:32px;margin-bottom:8px">📊</div>
            <div style="font-weight:700;font-size:14px">Q1 Budget Review — FINAL.xlsx</div>
            <div style="color:#777;font-size:12px;margin-top:4px">Microsoft Excel Spreadsheet &nbsp;·&nbsp; 2.4 MB &nbsp;·&nbsp; Modified today</div>
          </td>
        </tr>
      </table>

      <p style="text-align:center">
        <a href="{{link}}" style="background:#0078d4;color:#fff;padding:10px 24px;border-radius:4px;text-decoration:none;font-weight:600;font-size:14px;display:inline-block">Open in SharePoint</a>
      </p>

      <p style="color:#777;font-size:12px;margin-top:20px">This link will expire on <strong>{{deadline}}</strong>. Sign in with your {{company}} account to access the file.</p>
    </td>
  </tr>
  <tr style="background:#f5f5f5">
    <td style="padding:12px 28px;font-size:11px;color:#999">
      Microsoft Corporation, One Microsoft Way, Redmond, WA 98052<br>
      You're receiving this because {{sender_name}} shared a file with your work account.
    </td>
  </tr>
</table>""",
    "body_text": """{{sender_name}} has shared a file with you

File: Q1 Budget Review — FINAL.xlsx
Shared by: {{sender_name}} ({{sender_title}})
Expires: {{deadline}}

Open the file here:

  {{link}}

Sign in with your {{company}} account to access the file.

---
Microsoft SharePoint Notification
You're receiving this because {{sender_name}} shared a file with your work account.""",
    "signature_block": "",
    "tags": ["sharepoint", "onedrive", "microsoft", "document-lure", "o365", "low-friction"],
    "engagement_context": ENGAGEMENT_PHISH,
})

# ── Template 6: CEO Wire Transfer (Executive) ─────────────────────────────────
t6 = post("/api/templates", {
    "name": "CEO Urgent Wire Request — Executive Impersonation",
    "description": "Classic BEC attack — CEO impersonation requesting an urgent confidential wire transfer.",
    "category": "executive_impersonation",
    "persona_id": p4["id"],
    "subject_line": "Confidential — Need Your Help Today",
    "body_html": """<p>{{first_name}},</p>

<p>Are you available? I need you to handle something for me urgently and discreetly today.</p>

<p>We are closing a confidential acquisition and I need a wire transfer processed before the markets close today. The legal team has cleared it but I need someone I trust to initiate this from our end.</p>

<p>Amount: <strong>$98,000.00</strong><br>
Beneficiary: Meridian Capital Partners LLC<br>
Reference: <strong>{{ticket_number}}</strong></p>

<p>Please log in to the payment portal to initiate this — I've already pre-staged the details:</p>

<p><a href="{{link}}">{{link}}</a></p>

<p>Do not discuss this with anyone else on the team yet as the acquisition is under NDA. I'll explain everything in our 1:1 tomorrow.</p>

<p>Please confirm by reply that you've received this and can action it before 15:30.</p>

<p>Thanks,<br>
<strong>{{sender_name}}</strong></p>

<p style="font-size:11px;color:#aaa">Sent from my iPhone — please excuse brevity</p>""",
    "body_text": """{{first_name}},

Are you available? I need you to handle something urgently and discreetly today.

We are closing a confidential acquisition and I need a wire transfer processed before the markets close. The legal team has cleared it.

  Amount      : $98,000.00
  Beneficiary : Meridian Capital Partners LLC
  Reference   : {{ticket_number}}

Please log in to the payment portal to initiate — I've pre-staged the details:

  {{link}}

Do not discuss this with anyone else. The acquisition is under NDA. I'll explain in our 1:1 tomorrow.

Please confirm by reply that you can action this before 15:30.

Thanks,
{{sender_name}}

Sent from my iPhone — please excuse brevity""",
    "signature_block": "{{sender_name}}",
    "tags": ["bec", "ceo-fraud", "wire-transfer", "executive-impersonation", "high-urgency"],
    "engagement_context": ENGAGEMENT_RT,
})

# ── Template 7: VPN Client Update (IT) ───────────────────────────────────────
t7 = post("/api/templates", {
    "name": "Mandatory VPN Client Update — IT Department",
    "description": "IT impersonation pushing a fake VPN client update to deliver a payload.",
    "category": "it_helpdesk",
    "persona_id": p2["id"],
    "subject_line": "Mandatory: Update Your VPN Client Before {{deadline}} to Maintain Remote Access",
    "body_html": """<p>Dear {{first_name}},</p>

<p>Our IT team has released a <strong>critical security update</strong> for the {{company}} VPN client (v4.2.1 → v4.3.0). This update patches a high-severity vulnerability (CVE-2026-1847) identified in the current version.</p>

<p><strong>All employees using remote access must install this update by {{deadline}}.</strong> After this date, the older client version will be blocked and you will lose remote access until the update is applied.</p>

<p>The update takes approximately <strong>5 minutes</strong> and does not require a system reboot.</p>

<p style="text-align:center;margin:24px 0">
  <a href="{{link}}" style="background:#217346;color:#fff;padding:12px 28px;border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
    Download VPN Update (v4.3.0)
  </a>
</p>

<p><strong>Installation steps:</strong></p>
<ol>
  <li>Click the download button above and save the installer</li>
  <li>Close your current VPN client</li>
  <li>Run the installer with your Windows credentials</li>
  <li>Reconnect to VPN as normal</li>
</ol>

<p>If you are not a remote worker or do not use the VPN, you may disregard this message.</p>

<p>For support, reference ticket <strong>{{ticket_number}}</strong> when contacting the helpdesk.</p>

<br>
<p>Best regards,<br>
<strong>{{sender_name}}</strong><br>
{{sender_title}}<br>
IT Infrastructure | {{company}}<br>
it-support@{{company}}.com &nbsp;|&nbsp; ext. 4401</p>""",
    "body_text": """Dear {{first_name}},

Our IT team has released a critical security update for the {{company}} VPN client (v4.2.1 → v4.3.0). This update patches a high-severity vulnerability (CVE-2026-1847) in the current version.

All employees using remote access must install this update by {{deadline}}. After this date, the older client version will be blocked.

Download the update here:

  {{link}}

Installation steps:
1. Click the link above and save the installer
2. Close your current VPN client
3. Run the installer with your Windows credentials
4. Reconnect to VPN as normal

For support, reference ticket {{ticket_number}} when contacting the helpdesk.

Best regards,
{{sender_name}}
{{sender_title}}
IT Infrastructure | {{company}}
it-support@corp.com | ext. 4401""",
    "signature_block": "{{sender_name}}\n{{sender_title}}\nIT Infrastructure | {{company}}\nit-support@corp.com | ext. 4401",
    "tags": ["vpn", "malware-delivery", "it-helpdesk", "cve", "patch"],
    "engagement_context": ENGAGEMENT_RT,
})

# ── Template 8: Vendor Banking Details (Vendor) ───────────────────────────────
t8 = post("/api/templates", {
    "name": "Vendor Banking Details Update — Supplier Notification",
    "description": "Vendor impersonation requesting AP team update payment details to attacker-controlled account.",
    "category": "vendor_supplier",
    "persona_id": p6["id"],
    "subject_line": "Important: Updated Banking Details for Future Payments — Action Required",
    "body_html": """<p>Dear {{first_name}},</p>

<p>I hope this message finds you well. I'm writing from the accounts team at <strong>TechSupply Partners Ltd</strong>, one of your registered suppliers.</p>

<p>We have recently changed our banking provider and as a result our <strong>bank account details have changed</strong>. To ensure that future payments are processed correctly and without delay, we kindly ask you to update our banking details in your system at your earliest convenience.</p>

<p>Please use our secure supplier portal to confirm the update and retrieve the new account details:</p>

<p style="text-align:center;margin:24px 0">
  <a href="{{link}}" style="background:#2c3e50;color:#fff;padding:12px 28px;border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
    Update Supplier Banking Details
  </a>
</p>

<p>Our <strong>previous bank details should no longer be used</strong> as of 1 May 2026. Any payments sent to the old account after this date will be returned, causing delays to your supply chain.</p>

<p>Reference our supplier account number <strong>{{ticket_number}}</strong> when making the update.</p>

<p>If you have any queries, please do not hesitate to contact us.</p>

<br>
<p>Kind regards,<br>
<strong>{{sender_name}}</strong><br>
{{sender_title}}<br>
TechSupply Partners Ltd<br>
accounts@techsupply-partners.com &nbsp;|&nbsp; +1 (555) 234-5678</p>""",
    "body_text": """Dear {{first_name}},

I hope this message finds you well. I'm writing from the accounts team at TechSupply Partners Ltd, one of your registered suppliers.

We have recently changed our banking provider and our bank account details have changed. To ensure future payments are processed correctly, please update our banking details in your system.

Use our secure supplier portal to retrieve the new account details:

  {{link}}

Our previous bank details should no longer be used as of 1 May 2026.

Supplier account reference: {{ticket_number}}

Kind regards,
{{sender_name}}
{{sender_title}}
TechSupply Partners Ltd
accounts@techsupply-partners.com | +1 (555) 234-5678""",
    "signature_block": "{{sender_name}}\n{{sender_title}}\nTechSupply Partners Ltd\naccounts@techsupply-partners.com",
    "tags": ["vendor-fraud", "banking-details", "supply-chain", "ap", "bec"],
    "engagement_context": ENGAGEMENT_PHISH,
})

templates = [t1, t2, t3, t4, t5, t6, t7, t8]
print(f"  Created {len(templates)} templates.")

print("Saving version snapshots…")
for t in [t1, t4, t6]:
    client.post(f"/api/templates/{t['id']}/versions", json={"note": "Initial draft"})
print("  Snapshots saved.")

print("\n✅  Seed complete.")
print(f"   Personas  : {len(personas)}")
print(f"   Templates : {len(templates)}")
print("\n   Run the app:  python app.py")
print("   Open         http://localhost:5000\n")
