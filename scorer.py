import re


class PersuasionScorer:
    DIMENSIONS = {
        "urgency": {
            "keywords": [
                "immediately", "urgent", "urgently", "within 24 hours", "expires",
                "deadline", "action required", "time-sensitive", "by end of day",
                "right away", "as soon as possible", "asap", "without delay",
                "expiring", "expires today", "last chance", "final notice",
                "time is running out", "must act now", "respond immediately",
                "critical", "time critical", "respond today", "act now",
            ],
            "weight": 1.5,
        },
        "authority": {
            "keywords": [
                "on behalf of", "as directed by", "ceo", "cfo", "cto", "ciso",
                "president", "vice president", "director", "manager", "executive",
                "official notice", "mandatory", "required by", "policy requires",
                "it department", "human resources", "hr department", "security team",
                "compliance team", "legal team", "management", "board of directors",
            ],
            "weight": 1.3,
        },
        "scarcity": {
            "keywords": [
                "limited", "only available", "one-time", "exclusive access",
                "temporary access", "link expires", "one time", "single use",
                "limited time", "restricted access", "exclusive", "unique link",
                "personal link", "unique access", "expires in",
            ],
            "weight": 1.2,
        },
        "social_proof": {
            "keywords": [
                "all employees", "your colleagues", "company-wide", "everyone has",
                "most of your team", "your department", "other users have",
                "already completed", "join your team", "as others have",
                "across the organization", "all staff", "your peers", "team members",
            ],
            "weight": 1.1,
        },
        "familiarity": {
            "keywords": [
                "office 365", "microsoft", "workday", "servicenow", "slack",
                "teams", "zoom", "sharepoint", "onedrive", "okta", "salesforce",
                "zendesk", "jira", "confluence", "google workspace", "docusign",
                "adobe sign", "box", "dropbox", "aws", "azure", "active directory",
            ],
            "weight": 1.2,
        },
        "fear": {
            "keywords": [
                "suspended", "terminated", "locked", "blocked", "disabled",
                "compliance violation", "legal action", "security breach",
                "unauthorized access", "account compromised", "data breach",
                "penalty", "fine", "disciplinary", "consequences", "at risk",
                "account will be", "loss of access", "account suspension",
                "failure to comply",
            ],
            "weight": 1.4,
        },
        "reciprocity": {
            "keywords": [
                "we have processed", "your request has been", "as a reminder",
                "we are pleased to inform", "we have updated", "your benefit",
                "we are reaching out to help", "for your convenience",
                "we have prepared", "as a valued employee", "we wanted to make sure",
                "we have arranged", "to help you", "for your protection",
                "we have set up",
            ],
            "weight": 1.0,
        },
    }

    SUGGESTIONS = {
        "urgency": (
            "Add time pressure language: include a specific deadline "
            '(e.g., "by end of business today", "within 24 hours") and consequences of inaction.'
        ),
        "authority": (
            "Reference an authoritative sender: add a sender title, department, "
            "or indicate the message is from senior leadership."
        ),
        "scarcity": (
            "Add scarcity framing: mention the link is unique, single-use, or time-limited."
        ),
        "social_proof": (
            'Reference colleagues or org-wide rollouts: "Your team has already completed…", '
            '"All employees are required to…"'
        ),
        "familiarity": (
            "Reference known internal tools or platforms the target uses "
            "to increase contextual authenticity."
        ),
        "fear": (
            "Add negative consequence framing: account suspension, access revocation, "
            "compliance penalties."
        ),
        "reciprocity": (
            "Frame as doing the recipient a favour: "
            '"We\'ve already prepared your account", "To protect your access…"'
        ),
    }

    def score(self, text: str) -> dict:
        text_lower = text.lower()
        sentences = re.split(r"[.!?]+", text)
        results = {}

        for dim, cfg in self.DIMENSIONS.items():
            hits = 0
            matched = []
            for kw in cfg["keywords"]:
                if kw.lower() in text_lower:
                    hits += 1
                    for sent in sentences:
                        if kw.lower() in sent.lower() and sent.strip():
                            candidate = sent.strip()
                            if candidate not in matched:
                                matched.append(candidate)
            raw = min(hits * cfg["weight"], 10)
            score = max(1.0, round(raw, 1)) if raw > 0 else 1.0
            results[dim] = {
                "score": score,
                "hits": hits,
                "matched_sentences": matched[:3],
            }

        total_weight = sum(c["weight"] for c in self.DIMENSIONS.values())
        overall = (
            sum(
                results[d]["score"] * self.DIMENSIONS[d]["weight"]
                for d in self.DIMENSIONS
            )
            / total_weight
        )

        suggestions = [
            {
                "dimension": d,
                "current_score": results[d]["score"],
                "suggestion": self.SUGGESTIONS[d],
            }
            for d in self.DIMENSIONS
            if results[d]["score"] < 4
        ]

        return {
            "overall": round(overall, 1),
            "dimensions": results,
            "suggestions": suggestions,
        }


class ReadabilityScorer:
    def score(self, text: str) -> dict:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return {
                "score": 0,
                "grade": "N/A",
                "assessment": "No text to analyse",
                "word_count": 0,
                "sentence_count": 0,
                "avg_words_per_sentence": 0,
            }

        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        num_sentences = max(len(sentences), 1)
        words = re.findall(r"\b\w+\b", text)
        num_words = max(len(words), 1)
        num_syllables = sum(self._count_syllables(w) for w in words)

        fk = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
        fk = max(0.0, min(100.0, fk))

        if fk >= 80:
            grade, assessment = "Too Simple", "Very easy — may read as unsophisticated"
        elif fk >= 60:
            grade, assessment = "Good", "Optimal — conversational and clear"
        elif fk >= 40:
            grade, assessment = "Moderate", "Fairly difficult"
        else:
            grade, assessment = "Too Complex", "Too complex — simplify for better effectiveness"

        return {
            "score": round(fk, 1),
            "grade": grade,
            "assessment": assessment,
            "word_count": num_words,
            "sentence_count": num_sentences,
            "avg_words_per_sentence": round(num_words / num_sentences, 1),
        }

    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        count, prev_vowel = 0, False
        for ch in word:
            is_v = ch in "aeiouy"
            if is_v and not prev_vowel:
                count += 1
            prev_vowel = is_v
        if word.endswith("e") and count > 1:
            count -= 1
        return max(1, count)


class RedFlagDetector:
    GENERIC_GREETINGS = [
        "dear user", "hello customer", "dear customer", "dear member",
        "dear account holder", "to whom it may concern",
        "dear sir or madam", "hello there",
    ]
    AGGRESSIVE = [
        "you will be terminated", "legal proceedings will", "police",
        "lawsuit", "arrest", "criminal charges",
    ]
    MISSPELLINGS = {
        "recieve": "receive",
        "occured": "occurred",
        "seperate": "separate",
        "definately": "definitely",
        "accomodate": "accommodate",
        "neccessary": "necessary",
    }

    def detect(self, subject: str, body_html: str, body_text: str) -> list:
        flags = []
        combined = (body_html + " " + body_text).lower()
        subject = subject or ""

        for g in self.GENERIC_GREETINGS:
            if g in combined:
                flags.append({
                    "check": "Generic Greeting",
                    "severity": "high",
                    "detail": f'Found generic greeting: "{g}"',
                    "fix": "Replace with {{first_name}} personalisation.",
                })
                break

        if subject and subject.upper() == subject and len(subject) > 5 and not subject.isnumeric():
            flags.append({
                "check": "ALL CAPS Subject",
                "severity": "high",
                "detail": "Subject line is entirely uppercase.",
                "fix": "Use title case or sentence case.",
            })

        excl = body_html.count("!") + body_text.count("!")
        if excl > 3:
            flags.append({
                "check": "Excessive Exclamation Marks",
                "severity": "medium",
                "detail": f"Found {excl} exclamation marks.",
                "fix": "Reduce to 1–2 maximum.",
            })

        if re.search(r"https?://\d{1,3}(?:\.\d{1,3}){3}", body_html + body_text):
            flags.append({
                "check": "Raw IP Address in Link",
                "severity": "high",
                "detail": "Link contains a raw IP address.",
                "fix": "Use a convincing domain name instead.",
            })

        if re.search(r"<a[^>]*>https?://[^<]+</a>", body_html, re.IGNORECASE):
            flags.append({
                "check": "URL as Link Text",
                "severity": "medium",
                "detail": "A hyperlink shows the raw URL as its visible text.",
                "fix": 'Use descriptive anchor text like "Click here to verify".',
            })

        sig_indicators = [
            "regards", "sincerely", "best", "thanks", "thank you",
            "{{sender_name}}", "{{sender_title}}",
        ]
        if not any(s in combined for s in sig_indicators):
            flags.append({
                "check": "Missing Signature Block",
                "severity": "medium",
                "detail": "No signature block detected.",
                "fix": "Add a professional signature with name, title, company.",
            })

        for term in self.AGGRESSIVE:
            if term in combined:
                flags.append({
                    "check": "Overly Aggressive Urgency",
                    "severity": "high",
                    "detail": f'Contains extreme threat language: "{term}"',
                    "fix": "Soften — use account suspension/access loss instead.",
                })

        attachment_refs = ["attached", "attachment", "see the attached", "find attached", "enclosed"]
        if any(r in combined for r in attachment_refs) and "{{attachment}}" not in combined:
            flags.append({
                "check": "Attachment Reference Without Token",
                "severity": "low",
                "detail": "Template references an attachment but has no {{attachment}} token.",
                "fix": "Add {{attachment}} token or remove the reference.",
            })

        for wrong, correct in self.MISSPELLINGS.items():
            if wrong in combined:
                flags.append({
                    "check": "Spelling Error",
                    "severity": "medium",
                    "detail": f'Possible misspelling: "{wrong}" → "{correct}"',
                    "fix": f'Replace "{wrong}" with "{correct}".',
                })

        return flags
