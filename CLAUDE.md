## AI Provider Rule
ALL AI features in this project use Gemini API only.
- Key source: config.GEMINI_KEY (Railway env var) or gemini_key.txt (local)
- Model: gemini-2.5-pro-exp-03-25 — ALWAYS use this model
- Never use gemini-2.0-flash or any older model
- Never use OpenAI, Anthropic Claude API, or any other provider
- This rule applies to: translation, JD generation, announcements,
  evaluations, any future AI feature
