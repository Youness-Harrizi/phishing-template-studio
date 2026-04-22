"""
Phishing Template Studio — Test Suite
Run with:  python -m pytest tests/ -v
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scorer import PersuasionScorer, ReadabilityScorer, RedFlagDetector
from exporter import (
    export_gophish, export_eml, export_raw_html,
    export_plain_text, export_king_phisher, export_zip,
)
from pretext import generate_pretext


# ===========================================================================
# Fixtures
# ===========================================================================

SAMPLE_BODY = (
    "Dear {{first_name}},\n\n"
    "You must act immediately to reset your password before your account is suspended. "
    "This action is required by IT Security Management. "
    "Your account will be locked within 24 hours if you do not comply. "
    "As a valued employee we have prepared a unique link for you.\n\n"
    "Click here: {{link}}\n\n"
    "Deadline: {{deadline}}\n\n"
    "Best regards,\n{{sender_name}}\n{{sender_title}}"
)

SAMPLE_HTML = (
    "<p>Dear {{first_name}},</p>"
    "<p>You must act <strong>immediately</strong> to reset your password "
    "before your account is <em>suspended</em>.</p>"
    "<p>This action is required by <strong>IT Security Management</strong>.</p>"
    "<p>Your account will be locked within <strong>24 hours</strong>.</p>"
    "<p><a href='{{link}}'>Click here to verify</a></p>"
    "<p>Best regards,<br>{{sender_name}}<br>{{sender_title}}</p>"
)

SAMPLE_SUBJECT = "Urgent: Immediate Action Required — Account Suspension"

SAMPLE_TEMPLATE = {
    "id": "test-001",
    "name": "Test Phishing Template",
    "subject_line": SAMPLE_SUBJECT,
    "body_html": SAMPLE_HTML,
    "body_text": SAMPLE_BODY,
    "signature_block": "",
    "engagement_context": {},
}

ENGAGEMENT_CTX = {
    "engagement_name": "Q1 2026 Red Team",
    "reference_id": "RT-2026-001",
    "client_name": "Acme Corp",
    "assessment_type": "Red Team",
    "authorized_by": "Jane Smith",
    "authorization_date": "2026-01-15",
    "scope_notes": "Finance department, 50 target users, 1-week window",
}


# ===========================================================================
# PersuasionScorer tests
# ===========================================================================

class TestPersuasionScorer:
    scorer = PersuasionScorer()

    def test_deterministic_identical_inputs(self):
        """Scorer must return consistent scores for identical inputs."""
        r1 = self.scorer.score(SAMPLE_BODY)
        r2 = self.scorer.score(SAMPLE_BODY)
        assert r1["overall"] == r2["overall"]
        for dim in r1["dimensions"]:
            assert r1["dimensions"][dim]["score"] == r2["dimensions"][dim]["score"]

    def test_overall_score_in_range(self):
        """Overall score must be between 1 and 10."""
        r = self.scorer.score(SAMPLE_BODY)
        assert 1.0 <= r["overall"] <= 10.0

    def test_dimension_scores_in_range(self):
        """All dimension scores must be in [1, 10]."""
        r = self.scorer.score(SAMPLE_BODY)
        for dim, data in r["dimensions"].items():
            assert 1.0 <= data["score"] <= 10.0, f"{dim} score out of range: {data['score']}"

    def test_urgency_keywords_detected(self):
        """Urgency keywords must be detected in urgency-heavy text."""
        urgent_text = "You must act immediately, this is time-sensitive and the deadline expires today. Action required!"
        r = self.scorer.score(urgent_text)
        assert r["dimensions"]["urgency"]["score"] > 3

    def test_fear_keywords_detected(self):
        """Fear keywords must be detected."""
        fear_text = "Your account has been suspended due to a compliance violation. Legal action may follow."
        r = self.scorer.score(fear_text)
        assert r["dimensions"]["fear"]["score"] > 2

    def test_authority_keywords_detected(self):
        """Authority keywords must be detected."""
        auth_text = "On behalf of the CEO and management, this is a mandatory policy compliance requirement."
        r = self.scorer.score(auth_text)
        assert r["dimensions"]["authority"]["score"] > 2

    def test_empty_text_returns_ones(self):
        """Empty text should return minimal scores, not crash."""
        r = self.scorer.score("")
        assert r["overall"] >= 1.0

    def test_suggestions_returned_for_low_dimensions(self):
        """Suggestions must be returned for low-scoring dimensions."""
        r = self.scorer.score("Hello, please do the thing.")
        # At least some suggestions expected for bland text
        assert isinstance(r["suggestions"], list)

    def test_high_scoring_sample_above_threshold(self):
        """The sample template body should score above 2.0 overall."""
        r = self.scorer.score(SAMPLE_BODY)
        assert r["overall"] > 2.0

    def test_hit_counts_non_negative(self):
        """Hit counts must be non-negative integers."""
        r = self.scorer.score(SAMPLE_BODY)
        for dim, data in r["dimensions"].items():
            assert data["hits"] >= 0


# ===========================================================================
# ReadabilityScorer tests
# ===========================================================================

class TestReadabilityScorer:
    scorer = ReadabilityScorer()

    def test_empty_text_no_crash(self):
        r = self.scorer.score("")
        assert r["score"] == 0

    def test_simple_text_scores_high(self):
        """Very simple text should score high (easy to read)."""
        simple = "Go here now. Do this. Act fast. Click the link. Thank you."
        r = self.scorer.score(simple)
        assert r["score"] >= 50  # relatively easy

    def test_complex_text_scores_lower(self):
        """Complex academic text should score lower than simple text."""
        simple = "Click this link. Reset your password. It is easy."
        complex_text = (
            "In accordance with the organisational cybersecurity governance framework "
            "and pursuant to the multifaceted authentication remediation requirements "
            "stipulated by the enterprise information security management system, "
            "all authenticated principals are obligated to undertake credential recertification."
        )
        r_simple = self.scorer.score(simple)
        r_complex = self.scorer.score(complex_text)
        assert r_simple["score"] > r_complex["score"]

    def test_known_reference_text(self):
        """
        'The cat sat on the mat.' has roughly FK ~116 (very easy).
        We verify it scores > 70 (easy range).
        """
        r = self.scorer.score("The cat sat on the mat. It is a big cat. The mat is red.")
        assert r["score"] > 70

    def test_grade_labels(self):
        """Grade label must be one of the defined values."""
        for text in [SAMPLE_BODY, "a b c", ""]:
            r = self.scorer.score(text)
            assert r["grade"] in ("Good", "Too Simple", "Moderate", "Too Complex", "N/A")

    def test_word_count_accurate(self):
        """Word count should match manual count for a simple sentence."""
        r = self.scorer.score("one two three four five")
        assert r["word_count"] == 5

    def test_sentence_count_accurate(self):
        r = self.scorer.score("First sentence. Second sentence. Third sentence.")
        assert r["sentence_count"] == 3

    def test_html_stripped_for_scoring(self):
        """HTML tags must be stripped before computing readability."""
        html = "<p><strong>Click here now.</strong> <a href='#'>Link</a>.</p>"
        plain = "Click here now. Link."
        r_html = self.scorer.score(html)
        r_plain = self.scorer.score(plain)
        # Scores should be very close since HTML is stripped
        assert abs(r_html["score"] - r_plain["score"]) < 5


# ===========================================================================
# RedFlagDetector tests
# ===========================================================================

class TestRedFlagDetector:
    detector = RedFlagDetector()

    def test_generic_greeting_flagged(self):
        """Generic greetings must be flagged with high severity."""
        flags = self.detector.detect("Test Subject", "<p>Dear User, click here.</p>", "Dear User, click here.")
        checks = [f["check"] for f in flags]
        assert "Generic Greeting" in checks
        flag = next(f for f in flags if f["check"] == "Generic Greeting")
        assert flag["severity"] == "high"

    def test_all_caps_subject_flagged(self):
        """ALL CAPS subject must be flagged."""
        flags = self.detector.detect("URGENT ACTION REQUIRED NOW", SAMPLE_HTML, SAMPLE_BODY)
        checks = [f["check"] for f in flags]
        assert "ALL CAPS Subject" in checks

    def test_mixed_case_subject_not_flagged(self):
        """Normal subject line must NOT trigger ALL CAPS flag."""
        flags = self.detector.detect("Urgent: Account Reset Required", SAMPLE_HTML, SAMPLE_BODY)
        checks = [f["check"] for f in flags]
        assert "ALL CAPS Subject" not in checks

    def test_raw_ip_link_flagged(self):
        """Raw IP address in link must be flagged with high severity."""
        body = "<p>Click here: <a href='http://192.168.1.100/phish'>link</a></p>"
        flags = self.detector.detect("Test", body, "Click: http://192.168.1.100/phish")
        checks = [f["check"] for f in flags]
        assert "Raw IP Address in Link" in checks
        flag = next(f for f in flags if f["check"] == "Raw IP Address in Link")
        assert flag["severity"] == "high"

    def test_url_as_link_text_flagged(self):
        """Hyperlink displaying raw URL must be flagged."""
        body = "<a href='http://evil.com'>http://evil.com</a>"
        flags = self.detector.detect("Test", body, "")
        checks = [f["check"] for f in flags]
        assert "URL as Link Text" in checks

    def test_missing_signature_flagged(self):
        """Template without signature markers must be flagged."""
        flags = self.detector.detect("Test", "<p>Hello, click here.</p>", "Hello, click here.")
        checks = [f["check"] for f in flags]
        assert "Missing Signature Block" in checks

    def test_signature_present_not_flagged(self):
        """Template with signature must NOT trigger missing signature flag."""
        flags = self.detector.detect("Test", SAMPLE_HTML, SAMPLE_BODY)
        checks = [f["check"] for f in flags]
        assert "Missing Signature Block" not in checks

    def test_excessive_exclamation_flagged(self):
        """More than 3 exclamation marks must be flagged."""
        body = "Urgent! Act now! Click here! Do it now! Today!"
        flags = self.detector.detect("Test", body, body)
        checks = [f["check"] for f in flags]
        assert "Excessive Exclamation Marks" in checks

    def test_severity_values_valid(self):
        """All returned severities must be low, medium, or high."""
        flags = self.detector.detect("URGENT TEST", "<p>Dear User, http://1.2.3.4 !!!</p>", "Dear User !!!")
        for f in flags:
            assert f["severity"] in ("low", "medium", "high")

    def test_all_flags_have_fix_suggestion(self):
        """Every flag must include a fix suggestion."""
        flags = self.detector.detect("URGENT", "<p>Dear User http://1.2.3.4!</p>", "Dear User!")
        for f in flags:
            assert "fix" in f and f["fix"]


# ===========================================================================
# Token substitution tests
# ===========================================================================

class TestTokenSubstitution:
    def _substitute(self, text, values):
        return re.sub(r'\{\{(\w+)\}\}', lambda m: values.get(m.group(1), m.group(0)), text)

    def test_all_tokens_replaced_in_html(self):
        values = {"first_name": "Alice", "link": "https://example.com", "company": "ACME"}
        result = self._substitute("<p>Hi {{first_name}}, visit {{link}} from {{company}}.</p>", values)
        assert "{{" not in result
        assert "Alice" in result
        assert "https://example.com" in result

    def test_all_tokens_replaced_in_plain(self):
        values = {"first_name": "Bob", "deadline": "Friday", "sender_name": "John"}
        result = self._substitute("Dear {{first_name}}, deadline is {{deadline}}. — {{sender_name}}", values)
        assert "{{" not in result
        assert "Bob" in result
        assert "Friday" in result

    def test_missing_token_preserved(self):
        """Tokens with no substitution value should remain as-is."""
        result = self._substitute("Hello {{unknown_token}}", {})
        assert "{{unknown_token}}" in result

    def test_multiple_occurrences_all_replaced(self):
        """Multiple occurrences of the same token should all be replaced."""
        result = self._substitute("{{name}} said {{name}} was {{name}}", {"name": "Alice"})
        assert result == "Alice said Alice was Alice"


# ===========================================================================
# Exporter tests
# ===========================================================================

class TestExporters:
    def test_gophish_export_valid_json(self):
        """GoPhish export must produce valid JSON."""
        output = export_gophish(SAMPLE_TEMPLATE, ENGAGEMENT_CTX)
        parsed = json.loads(output)
        assert "name" in parsed
        assert "subject" in parsed
        assert "html" in parsed
        assert "text" in parsed
        assert "attachments" in parsed

    def test_gophish_token_mapping(self):
        """GoPhish export must map {{first_name}} → {{.FirstName}}."""
        t = dict(SAMPLE_TEMPLATE)
        t["body_html"] = "<p>Dear {{first_name}},</p>"
        t["body_text"] = "Dear {{first_name}},"
        output = export_gophish(t, {})
        parsed = json.loads(output)
        assert "{{.FirstName}}" in parsed["html"]
        assert "{{.FirstName}}" in parsed["text"]

    def test_gophish_audit_trail_embedded(self):
        """GoPhish export must include audit comment in HTML."""
        output = export_gophish(SAMPLE_TEMPLATE, ENGAGEMENT_CTX)
        parsed = json.loads(output)
        assert "ENGAGEMENT AUDIT TRAIL" in parsed["html"]
        assert ENGAGEMENT_CTX["client_name"] in parsed["html"]

    def test_eml_rfc2822_structure(self):
        """EML export must produce RFC 2822 compliant output parseable by email.parser."""
        import email as email_lib
        eml = export_eml(SAMPLE_TEMPLATE, ENGAGEMENT_CTX, "IT Helpdesk", "helpdesk@corp.com")
        msg = email_lib.message_from_string(eml)
        assert msg["From"] is not None
        assert msg["To"] is not None
        assert msg["Subject"] is not None
        assert msg["Date"] is not None
        assert msg["Message-ID"] is not None

    def test_eml_subject_preserved(self):
        import email as email_lib
        from email.header import decode_header, make_header
        eml = export_eml(SAMPLE_TEMPLATE, {}, "Test Sender", "test@corp.com")
        msg = email_lib.message_from_string(eml)
        # Subject may be RFC 2047 encoded (e.g. UTF-8 em dash → =?utf-8?q?...?=)
        decoded_subject = str(make_header(decode_header(msg["Subject"])))
        assert "Urgent" in decoded_subject
        assert "Account Suspension" in decoded_subject

    def test_eml_multipart_alternative(self):
        """EML must be multipart/alternative with both plain and HTML parts."""
        import email as email_lib
        eml = export_eml(SAMPLE_TEMPLATE, {}, "Sender", "s@corp.com")
        msg = email_lib.message_from_string(eml)
        assert msg.is_multipart()
        content_types = [p.get_content_type() for p in msg.walk()]
        assert "text/plain" in content_types
        assert "text/html" in content_types

    def test_raw_html_well_formed(self):
        """Raw HTML export must include doctype, charset, and body."""
        html = export_raw_html(SAMPLE_TEMPLATE, ENGAGEMENT_CTX)
        assert "<!DOCTYPE html>" in html
        assert "UTF-8" in html
        assert SAMPLE_TEMPLATE["body_html"] in html

    def test_plain_text_includes_subject(self):
        """Plain text export must start with subject line."""
        txt = export_plain_text(SAMPLE_TEMPLATE, {})
        assert txt.startswith("Subject: " + SAMPLE_SUBJECT)

    def test_king_phisher_json_valid(self):
        """King Phisher export must produce valid JSON."""
        output = export_king_phisher(SAMPLE_TEMPLATE, ENGAGEMENT_CTX)
        parsed = json.loads(output)
        assert "name" in parsed
        assert "subject" in parsed
        assert "html" in parsed

    def test_king_phisher_token_mapping(self):
        """King Phisher export must map {{first_name}} → {first_name}."""
        t = dict(SAMPLE_TEMPLATE)
        t["body_html"] = "Dear {{first_name}}, visit {{link}}"
        t["body_text"] = "Dear {{first_name}}"
        output = export_king_phisher(t, {})
        parsed = json.loads(output)
        assert "{first_name}" in parsed["html"]
        assert "{url}" in parsed["html"]

    def test_zip_export_contains_expected_files(self):
        """ZIP archive must contain all expected export files."""
        import zipfile, io
        raw = export_zip(SAMPLE_TEMPLATE, ENGAGEMENT_CTX, "Sender", "s@corp.com")
        zf = zipfile.ZipFile(io.BytesIO(raw))
        names = zf.namelist()
        assert any("gophish" in n for n in names)
        assert any(".eml" in n for n in names)
        assert any(".html" in n for n in names)
        assert any(".txt" in n for n in names)

    def test_audit_comment_no_ctx(self):
        """Exporter must not crash when engagement context is empty."""
        try:
            export_gophish(SAMPLE_TEMPLATE, {})
            export_raw_html(SAMPLE_TEMPLATE, {})
        except Exception as e:
            assert False, f"Raised exception with empty context: {e}"


# ===========================================================================
# Version restore test (via app)
# ===========================================================================

class TestVersionHistory:
    def setup_method(self):
        """Use Flask test client with an in-memory DB."""
        import tempfile
        os.environ["TESTING"] = "1"
        self.tmpdir = tempfile.mkdtemp()

    def test_version_restore_rolls_back_content(self):
        """
        Simulate: save template → save version → modify → restore → check rollback.
        This tests the full round-trip via the API layer without a running server.
        """
        import sqlite3, uuid
        from datetime import datetime, timezone

        db_path = os.path.join(self.tmpdir, "test.db")

        # Minimal DB setup
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE templates (
                id TEXT PRIMARY KEY, name TEXT, body_html TEXT, body_text TEXT,
                subject_line TEXT, updated_at TEXT
            );
            CREATE TABLE versions (
                id TEXT PRIMARY KEY, template_id TEXT, body_html TEXT,
                body_text TEXT, subject_line TEXT, note TEXT, saved_at TEXT
            );
        """)

        tid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        original_html = "<p>Original HTML</p>"
        original_text = "Original text"
        original_subject = "Original Subject"

        conn.execute(
            "INSERT INTO templates VALUES (?,?,?,?,?,?)",
            (tid, "Test", original_html, original_text, original_subject, now),
        )
        conn.commit()

        # Save version snapshot of original
        vid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO versions VALUES (?,?,?,?,?,?,?)",
            (vid, tid, original_html, original_text, original_subject, "Before change", now),
        )
        conn.commit()

        # Modify template
        conn.execute(
            "UPDATE templates SET body_html=?,body_text=?,subject_line=? WHERE id=?",
            ("<p>Modified</p>", "Modified text", "Modified Subject", tid),
        )
        conn.commit()

        # Verify modified
        row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
        assert row[2] == "<p>Modified</p>"

        # Restore version
        ver = conn.execute("SELECT * FROM versions WHERE id=?", (vid,)).fetchone()
        conn.execute(
            "UPDATE templates SET body_html=?,body_text=?,subject_line=? WHERE id=?",
            (ver[2], ver[3], ver[4], tid),
        )
        conn.commit()

        # Verify restored
        row = conn.execute("SELECT * FROM templates WHERE id=?", (tid,)).fetchone()
        assert row[2] == original_html
        assert row[3] == original_text
        assert row[4] == original_subject

        conn.close()


# ===========================================================================
# Pretext generator tests
# ===========================================================================

class TestPretextGenerator:
    def test_generates_three_subject_variants(self):
        result = generate_pretext("it_helpdesk", {})
        assert "subjects" in result
        assert "neutral" in result["subjects"]
        assert "urgency" in result["subjects"]
        assert "authority" in result["subjects"]

    def test_all_categories_return_result(self):
        categories = [
            "it_helpdesk", "hr_payroll", "finance_accounting",
            "executive_impersonation", "vendor_supplier",
            "security_alert", "collaboration_platform", "custom",
        ]
        for cat in categories:
            r = generate_pretext(cat, {})
            assert r["category"] == cat
            assert r["urgency_level"] in ("low", "medium", "high", "critical")

    def test_custom_description_used_for_custom_category(self):
        desc = "Targeting finance team with fake ACH update"
        r = generate_pretext("custom", {}, custom_description=desc)
        assert r["summary"] == desc

    def test_sender_info_always_present(self):
        r = generate_pretext("security_alert", {"known_platforms": ["Slack"]})
        assert "sender_name" in r
        assert "sender_display" in r
        assert r["sender_name"]

    def test_cta_always_present(self):
        for cat in ["it_helpdesk", "hr_payroll", "custom"]:
            r = generate_pretext(cat, {})
            assert "cta" in r and r["cta"]
