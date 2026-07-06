# AI integration layer.
#
# Wraps LLM providers behind narrow abstractions so the rest of the app depends
# on an interface, never on a concrete SDK. Routes and services must go through
# these clients — no direct provider calls elsewhere.

from app.services.ai.resume_parser_client import (
    AIParserError,
    AIResumeParserClient,
)

__all__ = ["AIResumeParserClient", "AIParserError"]
