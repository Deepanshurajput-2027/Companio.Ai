from typing import Any

from pydantic import BaseModel, Field


class Education(BaseModel):
    institution: str
    degree: str
    field: str
    cgpa: float | None = None
    start_year: int | None = None
    end_year: int | None = None


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class Experience(BaseModel):
    company: str
    role: str
    duration: str | None = None
    description: str
    skills_used: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    name: str
    headline: str
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    social_links: dict[str, str | None] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=30)
    job_description: str | None = Field(default=None, max_length=20000)


class MatchRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=20000)


class MatchResponse(BaseModel):
    score: float
    matching_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    experience_requirement_met: bool | None
    recommendation: str
    caveats: list[str] = Field(default_factory=list)


def profile_as_text(profile: CandidateProfile) -> str:
    return profile.model_dump_json(indent=2)


def model_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        return value.model_dump_json(indent=2)
    return str(value)
