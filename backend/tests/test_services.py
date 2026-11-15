import json

from app.models import CandidateProfile
from app.services import build_system_prompt, extract_document_text


def test_profile_schema_accepts_template():
    profile = CandidateProfile.model_validate(
        json.loads(
            '{"name":"Test","headline":"Engineer","education":[],"skills":[],"projects":[],'
            '"experience":[],"achievements":[],"certifications":[],"social_links":{}}'
        )
    )
    assert profile.name == "Test"


def test_extract_document_text_rejects_unsupported_type():
    try:
        extract_document_text("resume.csv", b"name")
    except ValueError as error:
        assert "Unsupported file type" in str(error)
    else:
        raise AssertionError("Expected unsupported file type to fail")


def test_chat_prompt_requests_concise_overview_and_memory():
    profile = CandidateProfile(
        name="Test",
        headline="Engineer",
        education=[],
        skills=[],
        projects=[],
        experience=[],
        achievements=[],
        certifications=[],
        social_links={},
    )
    prompt = build_system_prompt(profile)
    assert "CONSTRAINT" in prompt
    assert "Do not repeat the entire profile" in prompt
    assert "FALLBACK" in prompt
    assert "EXAMPLE" in prompt
