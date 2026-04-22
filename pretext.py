"""Rule-based pretext generator — no external API required."""

PRETEXT_DATA = {
    "it_helpdesk": {
        "subjects": {
            "neutral":   "Action Required: IT System Update for Your Account",
            "urgency":   "URGENT: Complete MFA Enrollment Before Access Expires",
            "authority": "IT Security Team: Mandatory Password Reset Required",
        },
        "senders": {
            "name":    "IT Helpdesk",
            "display": "it-helpdesk@{{company_domain}}",
        },
        "summary": "A mandatory system update requires all employees to re-enrol their MFA and reset their password via the secure portal.",
        "cta": "Click the secure link to complete your verification within 24 hours.",
        "urgency_level": "high",
        "urgency_reason": "Account access at risk; time-boxed window creates pressure.",
    },
    "hr_payroll": {
        "subjects": {
            "neutral":   "Your Payslip for This Period Is Now Available",
            "urgency":   "Action Required: Benefits Enrollment Closes Friday",
            "authority": "HR Department: Mandatory Policy Acknowledgment Required",
        },
        "senders": {
            "name":    "HR Department",
            "display": "hr@{{company_domain}}",
        },
        "summary": "HR has released updated payroll information and requires employees to confirm benefit selections before the enrollment window closes.",
        "cta": "Log in to the HR portal to review and confirm your selections.",
        "urgency_level": "medium",
        "urgency_reason": "Enrollment deadline creates natural time pressure.",
    },
    "finance_accounting": {
        "subjects": {
            "neutral":   "Invoice #{{ticket_number}} Requires Your Approval",
            "urgency":   "Urgent: Wire Transfer Confirmation Needed by EOD",
            "authority": "Finance Team: Expense Report Requires Immediate Sign-Off",
        },
        "senders": {
            "name":    "Accounts Payable",
            "display": "ap@{{company_domain}}",
        },
        "summary": "An invoice or wire transfer requires the recipient's approval to avoid payment delays and potential vendor penalties.",
        "cta": "Review and approve the attached document to process the payment.",
        "urgency_level": "high",
        "urgency_reason": "Financial deadlines and vendor relationships create strong action incentive.",
    },
    "executive_impersonation": {
        "subjects": {
            "neutral":   "Quick Request — Need Your Help",
            "urgency":   "Confidential: Urgent Action Required Before Board Meeting",
            "authority": "From the Desk of {{sender_name}}: Board Document Review",
        },
        "senders": {
            "name":    "{{sender_name}}, {{sender_title}}",
            "display": "{{sender_name_lower}}@{{company_domain}}",
        },
        "summary": "The CEO/CFO is requesting a confidential, time-sensitive action from the recipient, bypassing normal approval channels due to urgency.",
        "cta": "Reply directly or click the link to complete the requested action.",
        "urgency_level": "critical",
        "urgency_reason": "Executive authority + confidentiality framing suppresses normal verification behaviour.",
    },
    "vendor_supplier": {
        "subjects": {
            "neutral":   "Updated Banking Details for Upcoming Payment",
            "urgency":   "Action Required: Contract Renewal Deadline Approaching",
            "authority": "Supplier Notification: Updated Account Information",
        },
        "senders": {
            "name":    "{{vendor_name}} Accounts Team",
            "display": "billing@{{vendor_domain}}",
        },
        "summary": "A vendor has sent updated banking details or contract documents requiring immediate acknowledgment to avoid service interruption.",
        "cta": "Update your records with the new banking details provided below.",
        "urgency_level": "high",
        "urgency_reason": "Financial accuracy and supply chain continuity create strong compliance motivation.",
    },
    "security_alert": {
        "subjects": {
            "neutral":   "Security Notice: Unusual Sign-In Detected",
            "urgency":   "ALERT: Your Account Has Been Locked — Immediate Action Required",
            "authority": "Security Team: Compliance Review — Response Required",
        },
        "senders": {
            "name":    "Security Operations Center",
            "display": "security@{{company_domain}}",
        },
        "summary": "A suspicious login or compliance issue has triggered a security review requiring the user to verify their identity immediately.",
        "cta": "Verify your identity via the secure link to restore account access.",
        "urgency_level": "critical",
        "urgency_reason": "Fear of account compromise drives immediate action without careful scrutiny.",
    },
    "collaboration_platform": {
        "subjects": {
            "neutral":   "{{sender_name}} Has Shared a Document With You",
            "urgency":   "Action Required: Meeting Notes Require Your Signature",
            "authority": "{{sender_name}} is Waiting — Please Review the Shared File",
        },
        "senders": {
            "name":    "{{platform_name}} Notifications",
            "display": "notifications@{{platform_domain}}",
        },
        "summary": "A colleague has shared a document or meeting resource via a collaboration platform, requiring the recipient to log in to access it.",
        "cta": "Click to open the shared document in {{platform_name}}.",
        "urgency_level": "low",
        "urgency_reason": "Low friction — mirrors legitimate platform notifications recipients see daily.",
    },
    "custom": {
        "subjects": {
            "neutral":   "Important: Action Required",
            "urgency":   "Urgent: Please Respond Immediately",
            "authority": "Official Notice: Response Required",
        },
        "senders": {
            "name":    "{{sender_name}}",
            "display": "{{sender_email}}",
        },
        "summary": "Custom pretext — define your own scenario using the pretext description field.",
        "cta": "Follow the instructions provided in the email body.",
        "urgency_level": "medium",
        "urgency_reason": "Varies based on custom scenario.",
    },
}

PLATFORM_DOMAINS = {
    "Office 365": "microsoft.com",
    "Slack": "slack.com",
    "Workday": "myworkday.com",
    "ServiceNow": "service-now.com",
    "Zoom": "zoom.us",
    "Google Workspace": "google.com",
    "Okta": "okta.com",
    "Salesforce": "salesforce.com",
}


def generate_pretext(category: str, persona: dict, custom_description: str = "") -> dict:
    data = PRETEXT_DATA.get(category, PRETEXT_DATA["custom"])

    company_domain = "corp.com"
    platform_name = persona.get("known_platforms", ["your portal"])[0] if persona.get("known_platforms") else "your portal"
    platform_domain = PLATFORM_DOMAINS.get(platform_name, "notifications.com")

    ctx = {
        "company_domain": company_domain,
        "platform_name": platform_name,
        "platform_domain": platform_domain,
        "vendor_name": "TechSupply Inc.",
        "vendor_domain": "techsupply-billing.com",
        "sender_name": "Michael Chen",
        "sender_name_lower": "mchen",
        "sender_title": "Chief Executive Officer",
        "ticket_number": "INV-20480",
    }

    def render(text: str) -> str:
        for k, v in ctx.items():
            text = text.replace("{{" + k + "}}", str(v))
        return text

    result = {
        "category": category,
        "subjects": {k: render(v) for k, v in data["subjects"].items()},
        "sender_name": render(data["senders"]["name"]),
        "sender_display": render(data["senders"]["display"]),
        "summary": custom_description if custom_description and category == "custom" else render(data["summary"]),
        "cta": render(data["cta"]),
        "urgency_level": data["urgency_level"],
        "urgency_reason": data["urgency_reason"],
    }
    return result
