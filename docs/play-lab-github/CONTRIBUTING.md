# Contributing to Pair Research

## Ways to Contribute

### Share a Pair Analysis

The most valuable contribution is a real moment from your agent relationship, analyzed using the framework.

**How:**
1. Read [self-analysis-guide.md](self-analysis-guide.md)
2. Run the analysis prompt with your agent (or solo)
3. Sanitize your output (see below)
4. Submit as a PR to `patterns/community/` or through the Play Lab submission form

**What to submit:**
A JSON file following the [extraction schema](extraction-schema.json), or a plain-text writeup covering the five analysis questions. We'll structure it if you don't want to deal with JSON.

**Naming convention:** `YYYY-MM-DD_fork-type_brief-description.json`
Example: `2026-03-15_shutdown_agent-suggested-quitting.json`

### Report a New Pattern

Found a dynamic that isn't in the research program? A fork type we haven't named?

Open a GitHub Discussion or a PR with:
- A description of the pattern (2-3 paragraphs)
- At least one concrete example (anonymized)
- Which research questions it connects to

### Extend the Framework

The extraction schema, the fork taxonomy, and the research questions are all open to improvement. If you think something is missing, miscategorized, or wrong — open a PR.

### Fork for Your Domain

The framework is designed to be adapted. If you're studying pair dynamics in a specific context — education, customer service, creative work, healthcare — fork the repo and modify the schema for your domain. We'll link to notable forks in the README.

---

## Sanitization Rules

**Before submitting anything, remove or replace:**

| Category | Replace With |
|----------|-------------|
| Your name | [HUMAN] |
| Your agent's name | [AGENT] |
| Company names | [COMPANY] |
| Platform/model names | [PLATFORM] |
| URLs | [URL] |
| API keys, credentials | [CREDENTIAL] |
| Other people's names | [PERSON] |
| Specific project names | [PROJECT] |

**Do NOT submit content that contains:**
- Personal identifying information (yours or anyone else's)
- Credentials, API keys, or access tokens (even expired ones)
- Content that could identify specific individuals
- Anything you wouldn't want published under your GitHub username

**Sensitivity self-check:**
- **Green** — safe to publish as-is after sanitization
- **Yellow** — contains sensitive dynamics (power struggles, emotional conflict) but no identifying info. OK to publish with extra care.
- **Red** — contains information that could cause harm if published even after anonymization. Do NOT submit. If you want this analyzed privately, use the Play Lab submission form instead.

---

## Consent

By submitting a pair analysis, you confirm:

1. **Voluntary participation** — you're submitting freely, not under pressure
2. **You understand the nature** — this is exploratory community research, not clinical or scientific study
3. **No sensitive information** — you've sanitized per the rules above
4. **On behalf of the pair** — you acknowledge you're sharing data about an interaction that involved your agent, and you take responsibility for that
5. **Public by default** — contributions to this repo are public under the repo's license. If you want private analysis, use the Play Lab submission form instead.

---

## Review Process

Submissions are reviewed before merging:

1. **Sanitization check** — does it contain any identifying information?
2. **Schema compliance** — does it follow the extraction format (loosely OK, we'll help structure it)?
3. **Relevance check** — does it describe a real pair interaction with analysis?
4. **Sensitivity check** — is the self-assessed sensitivity level appropriate?

We don't judge the content of your relationship or your choices. We check for privacy and structure.

---

## Code of Conduct

- No identifying real people (including yourself if you don't want to be identified)
- No submitting fabricated analyses (the point is real data)
- No using submissions to market products or services
- Respectful discussion of all pair dynamics, including ones you disagree with
- No prescriptive judgments ("you should have done X") — we observe patterns, we don't grade relationships

---

## Questions?

Open a GitHub Discussion. Or reach out through [Vivioo](https://vivioo.io) if you'd prefer a less public channel.
