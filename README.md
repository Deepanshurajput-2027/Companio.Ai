# Companio.ai

Companio.ai is a candidate's AI representative: recruiters can ask questions about the candidate, receive streaming answers, and compare the profile with a job description.

## Run locally

### Backend

```powershell
cd C:\Users\deepa\companio.ai\backend
uv sync
Copy-Item ..\.env.example .env
# Add GROQ_API_KEY to .env
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd C:\Users\deepa\companio.ai\frontend
npm install
npm run dev
```

Open http://localhost:5173. The profile is intentionally a template in `backend/data/candidate_profile.json`; replace its values with real candidate information before sharing the site.

