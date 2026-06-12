# Website Blog AI

AI-powered content discovery and SEO blog writer for **Odoo 19**. Two
autonomous AI agents monitor the news from your keywords and draft
SEO-optimized blog articles, fully integrated with Odoo's Website Blog.

> 🎥 **Demo video:** https://drive.google.com/drive/folders/1iz6obS2ibnniCNehkiN0uiKQNBhCRLEM

---

## Overview

The module automates editorial monitoring and content creation through two
agents:

### 🔍 Sniffer (news monitoring)
Runs on a schedule (every *X* days, configurable):
1. Performs a **real web search** from the user-defined keywords.
2. Identifies the most relevant topics.
3. Creates **blog proposals** in the backend, pending human validation.

Each proposal contains the six required fields:
- Suggested title
- Topic summary
- Identified context
- Recommended editorial angle
- Potential sources (clickable links)
- Relevance score (0–10) + selection justification

### ✍️ Rédacteur (article writer)
Runs **after a human validates a proposal**:
1. Optionally takes additional user instructions.
2. Generates a complete, **SEO-optimized article**.
3. Stores it as an **unpublished** `blog.post` for review.

Publication stays a **manual** action — articles are never auto-published.

---

## Workflow

1. Configure keywords (*Blog AI → Configuration → Keywords*)
2. The Sniffer runs automatically (or click **Run Sniffer Now**)
3. Proposals are created (*Blog AI → AI Blog → Proposals*)
4. A user validates a proposal
5. A user optionally adds extra instructions
6. The Rédacteur generates the article
7. A user reviews the article
8. A user publishes it manually on the website

---

## Requirements

- Odoo 19
- A Google **Gemini** API key (free tier works) — get one at
  <https://aistudio.google.com/apikey>

---

## Installation

1. Copy this module into your Odoo addons path (e.g. `extra-addons/`).
2. Update the apps list and install **Website Blog AI**.
3. Configure the API key (see below).

---

## Configuration

Go to **Blog AI → Configuration → Settings** (or *Settings → Blog AI*):

| Setting | Description |
|---|---|
| Provider | AI vendor (Gemini) |
| Request Timeout | Max seconds to wait for a response |
| API Key | Your Gemini API key |
| Model | Default `gemini-2.5-flash` |
| API Base URL | Endpoint base (for a proxy / different API version) |
| Run Every (days) | Sniffer monitoring frequency |
| Max Proposals per Run | How many topics per run |

Click **Test Connection** to verify the setup.

> 💡 Tip: keywords can be ambiguous (e.g. `mcp`). Use specific keywords or fill
> a keyword's **Note** to disambiguate — the Sniffer passes notes to the AI.

---

## Architecture

The AI layer is **abstracted** behind a vendor-neutral service
(`ai.provider`). Callers use only `generate()` / `generate_json()` and never a
concrete vendor API. The active provider is selected by a config parameter and
dispatched to a `_call_<provider>` method, so adding another provider means
adding one method — no caller changes.

| Component | Model | Type |
|---|---|---|
| AI abstraction | `ai.provider` | AbstractModel |
| Keywords | `ai.blog.keyword` | Model |
| Proposals | `ai.blog.proposal` | Model |
| Sniffer agent | `ai.sniffer` | AbstractModel |
| Rédacteur agent | `ai.redacteur` | AbstractModel |
| Settings | `res.config.settings` | TransientModel |

Generated articles reuse Odoo's **native SEO metadata** fields
(`website_meta_title`, `website_meta_description`, `website_meta_keywords`) —
the same fields Odoo's own SEO tool edits.

### Notable design decisions
- **Sniffer → JSON output** (plain-text fields parse reliably).
- **Rédacteur → delimiter output** (`###CONTENT###` last, raw): embedding HTML
  inside JSON breaks parsing on unescaped quotes/newlines, so the article body
  is delivered raw after a marker.
- **Real sources** come from the search grounding citations and render as
  clickable links.

---

## License

LGPL-3
