# GENAI-hackathon
# Parallel Self AI Lab (Flask + SQLite + Groq Chatbot)

A polished Flask project that simulates multiple versions of a user’s daily behavior, compares productivity modes, tracks journal patterns, exports reports, and now includes a Groq-powered conversational AI coach.

## Upgraded Features
- Login/Register with hashed passwords and role-based admin access.
- Personality profile sliders: introversion, boldness, creativity, sleep, and work/study hours.
- Parallel selves simulation: Base, Bold, Introverted, and Creative modes.
- AI-style scoring: readiness, balance, recovery, burnout risk, deep-work fit, collaboration fit, and creative-fit scoring.
- Run history, run detail pages, comparison workspace, and PDF export.
- Smart journal with search, mood filter, sentiment signal, streak, and themes.
- Admin dashboard with user management, password reset, platform analytics, mood analytics, and archetype analytics.
- **New Groq AI Chatbot** with personalized context from user profile, latest simulation, and journal signals.
- **Markdown answers + Bleach sanitization** so chatbot output looks like GPT while staying safer to display.
- Offline fallback chatbot mode, so the project still works before adding an API key.
- Improved dark/light theme visibility for lists, tables, cards, markdown, selects, alerts, and generated content.

## Recommended Groq Model
For a fast conversational chatbot, use:

```env
GROQ_MODEL=llama-3.1-8b-instant
GROQ_MAX_TOKENS=700
GROQ_TEMPERATURE=0.55
CHAT_INPUT_MAX_CHARS=1800
```

## Setup
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
# source .venv/bin/activate

pip install -r requirements.txt
```

## Configure Environment
Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

Then add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_MAX_TOKENS=700
GROQ_TEMPERATURE=0.55
```

If you do not add a Groq API key, the chatbot still opens and uses the built-in offline coach response.

## Run
```bash
python run.py
```

Open:

```text
http://127.0.0.1:5000
```

## Database
The SQLite database is created automatically at:

```text
instance/app.db
```

To reset the project database, stop Flask and delete `instance/app.db`.

## First Admin
The first registered user automatically becomes admin.

## Supervisor Demo Flow
1. Register the first account.
2. Complete onboarding sliders.
3. Generate a simulation from the dashboard.
4. Open the run detail page and show charts, strongest self, risks, and PDF export.
5. Open Compare Selves to show fit scoring.
6. Add a journal entry and show journal intelligence.
7. Open the AI Chatbot and ask: “Explain my latest simulation in simple words.”
8. Open Admin Analytics to show platform-level dashboard features.
