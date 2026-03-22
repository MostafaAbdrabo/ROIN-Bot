## AI Provider Rule
ALL AI features in this project use Gemini API only.
- Key source: config.GEMINI_KEY (Railway env var) or gemini_key.txt (local)
- Never use OpenAI, Anthropic Claude API, or any other provider
- Model: gemini-1.5-flash (fast + cheap) or gemini-1.5-pro (complex tasks)
- This rule applies to: translation, JD generation, announcements,
  evaluations, any future AI feature
