from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

FIELDS = ("event_name", "date", "start_time", "end_time", "timezone", "venue", "price",
          "registration_url", "audience", "tone")
CRITICAL = ("date", "start_time", "end_time", "timezone", "venue", "price", "registration_url")
FORMATS = ("linkedin", "email", "blog", "ads")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Fact(Strict):
    value: str = Field(min_length=1, max_length=1000)
    source_ids: list[str] = Field(min_length=1, max_length=20)
    quote: str = Field(min_length=1, max_length=2000)


class Plan(Strict):
    facts: dict[str, Fact]
    questions: list[str] = Field(max_length=10)
    approach: str = Field(min_length=1, max_length=3000)


class Draft(Strict):
    text: str = Field(min_length=20, max_length=6000)
    source_ids: list[str] = Field(min_length=1, max_length=20)


class Bundle(Strict):
    linkedin: Draft
    email: Draft
    blog: Draft
    ads: list[Draft] = Field(min_length=3, max_length=3)


class Issue(Strict):
    format: Literal["all", "linkedin", "email", "blog", "ads"]
    severity: Literal["blocking", "warning"]
    detail: str = Field(min_length=1, max_length=2000)


class Review(Strict):
    issues: list[Issue] = Field(max_length=30)
    summary: str = Field(min_length=1, max_length=3000)


class State(TypedDict, total=False):
    campaign_id: str
    status: str
    tool_message: dict
    tool_result: str
    evidence: list[dict]
    plan: dict
    facts: dict
    questions: list[dict]
    confirmations: dict
    clarification_history: list[dict]
    bundle: dict
    drafts: dict
    review_history: list[dict]
    revision_count: int
    failure: dict | None
    retry_node: str


class Handoff(Exception):
    def __init__(self, kind: str, message: str, retryable: bool = True):
        super().__init__(message)
        self.kind, self.message, self.retryable = kind, message, retryable
