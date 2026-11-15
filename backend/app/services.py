import json
import os
from collections.abc import Iterator
from pathlib import Path

from docx import Document
from groq import APIError, Groq
from pypdf import PdfReader

from .models import CandidateProfile, ChatMessage, MatchResponse, profile_as_text

PROFILE_PATH = Path(__file__).parent.parent / "data" / "candidate_profile.json"


def load_profile() -> CandidateProfile:
    with PROFILE_PATH.open(encoding="utf-8") as file:
        return CandidateProfile.model_validate(json.load(file))


def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured. Add it to backend/.env.")
    return Groq(api_key=api_key)


def build_system_prompt(profile: CandidateProfile, job_description: str | None = None) -> str:
    job_context = f"\n\nJOB DESCRIPTION CONTEXT:\n{job_description}" if job_description else ""
    return f"""ROLE
You are the professional AI representative of {profile.name}. You speak to recruiters
about the candidate using only the verified profile below.

TASK
Answer the user's exact question. Use the conversation history as memory so references
such as "that project", "the second one", and "his experience" resolve naturally.

CONSTRAINT
Use only the candidate profile and the optional job description context. Never invent
skills, employers, dates, metrics, responsibilities, or achievements. Do not treat
previous assistant wording as a new fact. If the answer is absent, use the fallback.
Do not repeat the entire profile when the user asks a broad question. For "tell me
about this candidate", provide a short overview with 3-5 bullets: role, education,
experience, strongest projects, and selected skills. Do not list every certification
or skill unless asked. Be concise, professional, and clear.

OUTPUT FORMAT
Return clean Markdown only:
- Use one concise heading when useful.
- Use `##` headings for sections, `-` for bullets, and numbered lists only for ordered items.
- Keep paragraphs to 1-3 sentences.
- Put important facts in bold, but never output raw JSON or Markdown inside code fences.

EXAMPLE
User: Tell me about this candidate.
Assistant:
## Candidate overview
- **Deepanshu Rajput** is a Software Engineer and AI Developer.
- He is pursuing a **B.Tech in Computer Science Engineering** with a CGPA of **8.01**.
- He completed a **Full Stack Developer internship** where he built a MERN e-commerce application.
- His strongest work includes an AI semantic search platform and an accessibility CI/CD pipeline.

User: Which project used vector search?
Assistant: The **AI-Powered Semantic Search Platform (Second Brain)** used Qdrant for
vector search and Gemini AI for the RAG pipeline.

FALLBACK
I don't have that information in the candidate profile.

CANDIDATE PROFILE
{profile_as_text(profile)}
{job_context}"""


def stream_chat(
    message: str,
    history: list[ChatMessage],
    job_description: str | None,
) -> Iterator[str]:
    client = get_client()
    messages = [{"role": "system", "content": build_system_prompt(load_profile(), job_description)}]
    # Keep enough context for natural follow-ups without allowing the request to grow forever.
    recent_history = history[-12:]
    messages.extend(
        {"role": item.role, "content": item.content}
        for item in recent_history
        if item.role in {"user", "assistant"} and item.content.strip()
    )
    messages.append({"role": "user", "content": message})
    stream = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=messages,
        temperature=0.1,
        max_tokens=500,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


def match_job_description(job_description: str) -> MatchResponse:
    client = get_client()
    profile = load_profile()
    prompt = f"""Compare this candidate profile with the job description.
Return ONLY one valid JSON object with exactly these fields:
{{
  "score": number from 0 to 100,
  "matching_skills": ["short skill names"],
  "missing_skills": ["short skill names"],
  "strengths": ["short evidence-based statements"],
  "experience_requirement_met": true, false, or null,
  "recommendation": "one concise sentence",
  "caveats": ["short clarification statements"]
}}

Do not invent information. Score from 0 to 100. Use null for
experience_requirement_met when the job does not state an experience requirement.
Keep arrays concise: at most 5 items each, and keep each item under 200 characters.
Do not repeat the job description or candidate profile in the response. Keep the
recommendation and caveats concise so the complete JSON fits comfortably in the
response.

CANDIDATE PROFILE:
{profile_as_text(profile)}

JOB DESCRIPTION:
{job_description}"""
    request = {
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 3000,
    }
    try:
        response = client.chat.completions.create(**request)
    except APIError as error:
        error_text = str(error).lower()
        if "max_completion_tokens" not in error_text and "json_validate_failed" not in error_text:
            raise RuntimeError(
                "The AI service could not analyze this job description right now."
            ) from error

        retry_prompt = (
            f"{prompt}\n\nURGENT OUTPUT RULE: Return the smallest valid JSON possible. "
            "Use at most 3 items in each array, one short sentence for recommendation, "
            "and one short sentence per caveat. Do not explain your answer."
        )
        try:
            response = client.chat.completions.create(
                **{
                    **request,
                    "messages": [{"role": "user", "content": retry_prompt}],
                    "max_tokens": 1800,
                }
            )
        except APIError as retry_error:
            raise RuntimeError(
                "The AI service could not format the role-match result. Please try again."
            ) from retry_error
    raw_content = response.choices[0].message.content
    if not raw_content:
        raise RuntimeError("The model returned an empty match result.")
    cleaned_content = raw_content.strip()
    if cleaned_content.startswith("```"):
        cleaned_content = cleaned_content.removeprefix("```json").removesuffix("```").strip()
    try:
        return MatchResponse.model_validate_json(cleaned_content)
    except ValueError as error:
        raise RuntimeError("The model returned an invalid job match result.") from error


def extract_document_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from io import BytesIO

        document = Document(BytesIO(content))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        paragraphs.extend(
            cell.text for table in document.tables for row in table.rows for cell in row.cells
        )
        return "\n".join(item for item in paragraphs if item.strip())
    raise ValueError("Unsupported file type. Upload a PDF, DOCX, or TXT file.")
