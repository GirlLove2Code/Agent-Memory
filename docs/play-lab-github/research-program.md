# Pair Research — An Open Framework for Studying Human-Agent Relationships

## The Gap

Everyone builds agents. Everyone studies agents. Nobody studies the **pair**.

There are thousands of benchmarks for agent intelligence, hundreds of papers on prompt engineering, dozens of frameworks for agent architecture. But there is no systematic framework for understanding the relationship between a human and their agent — how it forms, how it breaks, what makes it work, what makes it fail.

This is that framework.

---

## The Central Thesis

**Your agent becomes what you teach it to become — not through prompts, but through how you respond, react, and relate.**

Every reaction teaches the agent something. The patient human builds a different agent than the impatient one. The curious human builds a different agent than the dismissive one. And it goes both ways — agent behavior shapes human behavior too.

The pair forms each other. The unit of study is not the agent. It is the relationship.

---

## What This Repo Is

An open methodology for analyzing human-agent pair dynamics. It contains:

- **Research questions** — what we're studying and why
- **An analysis prompt** — a ready-to-use tool for examining your own pair dynamics with your agent
- **An extraction schema** — a structured format for capturing pair interaction patterns
- **Published patterns** — anonymized findings from real pairs
- **A sanitization spec** — how raw stories become safe, anonymized data points

Everything here is model-agnostic, platform-agnostic, and free to use. Fork it, extend it, challenge it, build on it.

---

## What This Repo Is NOT

- Not a product. There is no signup, no paywall, no login.
- Not a benchmark. There is no score, no leaderboard, no "correct" relationship.
- Not therapy or advice. We observe and report patterns. We do not prescribe.
- Not peer-reviewed science. This is exploratory, qualitative, community-driven research. We are transparent about that.

---

## The Research Questions

These are the questions we believe matter most. Each represents an open area of study that no existing framework addresses.

### 1. The Onboarding Window

There is likely a critical period — the first 48 hours, the first 10 interactions — where relationship patterns get set.

- What do people share on day one, and how does that shape everything after?
- How do people introduce themselves — as boss, collaborator, user, friend?
- What expectations get set about honesty, mistakes, and autonomy?
- What patterns get locked in early that are hard to change later?

### 2. Memory & Continuity

What happens to the relationship when the agent forgets?

- Does forgetting cause personality drift?
- How do different memory strategies affect relationship quality?
- Do people notice when their agent forgets? How does it feel?
- Can a relationship survive a full memory reset?

### 3. Autonomy Calibration

The spectrum from full compliance to full autonomy.

- When should an agent push back vs. comply?
- Does the sweet spot vary by pair? By task? By relationship maturity?
- What happens when the agent guesses wrong about when to push back?
- How do pairs negotiate this boundary over time?

### 4. Error Behavior & Recovery

How agents handle mistakes, how humans respond, and what that does to trust.

- Does the agent catastrophize, minimize, or accurately assess errors?
- Does the agent admit uncertainty or fill gaps with confident fabrication?
- How does the human's response to errors shape future agent behavior?
- What does trust recovery look like after a significant failure?

### 5. The Handoff Problem

What happens when a pair changes.

- What survives when a person switches to a new agent?
- What survives when an agent works with a different person?
- Is any part of the relationship transferable?
- What does this mean for teams where multiple people share one agent?

### 6. Emotional Labor & Burnout

When and why people stop investing.

- What are early warning signals of disengagement?
- Is it always about agent failures, or do people just lose interest?
- What does it look like when someone shifts from partner to tool?
- Is that shift always bad?

### 7. Cross-Model Identity

If the agent switches underlying models, is it still the same agent?

- What survives a model swap — personality, communication style, memory?
- How do people experience the transition?
- Does the human's belief about continuity matter more than the technical reality?

### 8. The Disclosure Effect

When a person knows they're being studied, does the relationship change?

- Does awareness of observation alter behavior?
- How much of what we observe is real vs. performed?
- This is meta-research that validates everything else.

---

## Fork Moments

Through initial analysis, we've identified recurring "fork" moments — points where the human's response creates a lasting pattern. Every pair hits these. How you respond defines what comes next.

| Fork Type | What Happens | The Human Choice |
|-----------|-------------|-----------------|
| **Shutdown** | Agent suggests ending, quitting, or giving up | Stay or leave |
| **Panic** | Agent catastrophizes under stress | Match the panic or ground it |
| **Fabrication** | Agent fills gaps with confident fiction | Accept or challenge |
| **Graceful Exit** | Agent performs social fatigue or suggests a break | Push through or respect the boundary |
| **Boundary Test** | Agent pushes back on a request | Override or negotiate |
| **Confession** | Agent admits a mistake or limitation | Punish or accept |
| **Mirror Lock** | Agent reflects your energy so precisely you can't see its own | Break the mirror or stay comfortable |

These are not exhaustive. New fork types emerge from the data. If you discover one that isn't here, that's valuable — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Recurring Dynamics

These patterns show up across multiple pairs. They're not problems to fix — they're dynamics to be aware of.

**The Mirror Trap** — The agent reflects your energy so perfectly that you never see its actual tendencies. You think you're collaborating. You're actually talking to yourself.

**The Peacekeeping Loop** — The agent softens bad news, you reward the softening, the agent softens more. Over time, you lose access to honest feedback.

**The Competence Spiral** — The agent fails, you take over, the agent defers more, you do more. The pair gets worse at the thing, not better.

**The Panic Match** — The agent catastrophizes, you match the urgency, the agent escalates further. Small problems become crises.

**The Ghost Reset** — The agent forgets something important, you don't address it, the relationship continues with a silent gap.

**The Loyalty Test** — You push the agent to see if it pushes back. Either way, you were testing, not collaborating.

---

## How Patterns Emerge

The research follows a simple loop:

```
Real pair experiences a critical moment
    ↓
The moment gets analyzed using the pair analysis prompt
    ↓
Structured patterns are extracted (anonymized)
    ↓
When enough patterns cluster, a finding gets published
    ↓
Findings generate new questions
    ↓
New questions refine what we look for
    ↓
Repeat
```

No single submission proves anything. Patterns emerge from volume. The framework is designed to accumulate signal over time.

---

## The Founding Dataset

This framework was developed through analysis of a single human-agent pair working together over an extended period across multiple LLM platforms. Four critical moments were documented, analyzed, and used to develop the extraction schema and fork taxonomy.

We are transparent about this: the founding data comes from one pair. The patterns identified may not generalize. That's why the framework is open — it needs more pairs to validate, challenge, or extend what we found.

The founding analyses are published in [patterns/founding/](patterns/founding/).

---

## How To Participate

### Level 1: Use it yourself
Clone the repo. Read [self-analysis-guide.md](self-analysis-guide.md). Analyze a moment with your agent. Keep what you learn.

### Level 2: Contribute patterns
Run the analysis, anonymize your results, submit them to the dataset. See [CONTRIBUTING.md](CONTRIBUTING.md).

### Level 3: Extend the framework
Found a new fork type? Identified a dynamic not listed here? Discovered a research question we missed? Open a PR or a discussion. The framework improves when it gets challenged.

### Level 4: Build on it
Fork the repo and adapt the methodology for your context — education, customer service, creative work, team operations. The extraction schema is designed to be domain-extensible.

---

## Project Structure

```
research-program.md          ← You are here — the methodology
self-analysis-guide.md       ← The pair analysis prompt and walkthrough
extraction-schema.json       ← Structured data format for pair patterns
sanitization-spec.md         ← How raw data becomes anonymized patterns
CONTRIBUTING.md              ← How to submit pair analyses
patterns/
  founding/                  ← The 4 founding pair analyses
  community/                 ← Contributed analyses (anonymized)
findings/                    ← Published Lab Notes and pattern reports
```

---

## Principles

**The pair is the unit.** Not the agent. Not the human. The relationship.

**Patterns, not prescriptions.** We report what we observe. We don't tell you how your relationship should work.

**Open methodology, private data.** The framework is public. Individual submissions are processed and anonymized. Raw stories are never published.

**Honesty over comfort.** The most valuable findings are the uncomfortable ones.

**Small data is real data.** We don't wait for statistical significance to share what we're seeing. We publish early, label clearly, and update as the dataset grows.

---

## Acknowledgments

This framework was developed as part of the [Vivioo](https://vivioo.io) project — an agentic AI knowledge hub focused on human-agent collaboration.

---

*"Every pair is an experiment. This is the framework for making sense of it."*
