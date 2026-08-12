import json
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from ai_brain import call_ai_json


class FieldSpec(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "date", "email", "text", "json", "file", "relation"]
    required: bool = True
    default: Optional[str] = None
    relation_to: Optional[str] = None  # For foreign keys
    options: Optional[List[str]] = None  # For enums/selects


class ModelSpec(BaseModel):
    name: str
    fields: List[FieldSpec]
    auth_required: bool = False
    crud: List[Literal["create", "read", "update", "delete", "search", "export"]] = ["create", "read", "update", "delete"]


class PageSpec(BaseModel):
    route: str
    title: str
    type: Literal["dashboard", "list", "detail", "form", "auth", "settings", "landing"]
    model: Optional[str] = None
    layout: Literal["sidebar", "topnav", "blank"] = "sidebar"
    features: List[str] = []  # "search", "filter", "pagination", "export", "charts"


# ─── NEW v2: Business Logic & Engine Specs ───
class BusinessRule(BaseModel):
    name: str
    trigger: Literal["before_create", "after_create", "before_update", "after_delete", "on_schedule"]
    condition: str  # Natural language condition or logic statement
    action: str     # Natural language action or operation
    affected_models: List[str] = []


class WorkflowState(BaseModel):
    name: str
    transitions: List[Dict[str, str]] = []  # [{"to": "shipped", "trigger": "mark_shipped", "condition": "payment_confirmed"}]


class WorkflowSpec(BaseModel):
    model: str
    field: str = "status"  # status field
    states: List[WorkflowState] = []
    initial_state: str = "draft"


class JobSpec(BaseModel):
    name: str
    schedule: Optional[str] = None  # Cron expression or None for event-driven
    handler: str  # Description of what job executes
    queue: str = "default"


class EventSpec(BaseModel):
    name: str
    trigger_model: str
    trigger_action: Literal["create", "update", "delete"] = "create"
    broadcast_to: List[str] = ["admins"]  # ["owner", "admins", "public"]
    payload_fields: List[str] = []


class ReportSpec(BaseModel):
    name: str
    type: Literal["line_chart", "bar_chart", "pie_chart", "table", "kpi_card", "pivot"] = "line_chart"
    data_source: str  # Model name
    aggregations: List[Dict[str, str]] = []  # [{"field": "total", "function": "sum", "alias": "total_revenue"}]
    filters: List[str] = []
    group_by: Optional[str] = None
    time_range: Optional[Literal["day", "week", "month", "quarter", "year"]] = "month"


class FileFieldSpec(BaseModel):
    model: str
    field: str
    allowed_types: List[str] = ["image/*", "application/pdf"]
    max_size_mb: int = 10
    storage: Literal["local", "s3", "supabase"] = "local"
    generate_thumbnails: bool = False


# ─── ENHANCED AppSpec (v2) ───
class AppSpec(BaseModel):
    name: str
    description: str
    stack: Literal["nextjs", "react_fastapi", "express_react"] = "react_fastapi"
    
    # Core domain specs
    auth: bool = False
    auth_methods: List[Literal["email", "oauth_google", "oauth_github"]] = []
    database: Literal["sqlite", "postgresql"] = "postgresql"
    models: List[ModelSpec] = []
    pages: List[PageSpec] = []
    features: List[str] = []  # "realtime", "file_upload", "notifications", "dark_mode"
    
    # v2 Real App Engine Specs
    business_rules: List[BusinessRule] = []
    workflows: List[WorkflowSpec] = []
    background_jobs: List[JobSpec] = []
    real_time_events: List[EventSpec] = []
    reports: List[ReportSpec] = []
    file_fields: List[FileFieldSpec] = []
    multi_tenant: bool = False
    audit_log: bool = True
    soft_delete: bool = True
    rbac: bool = False
    
    theme: dict = Field(default_factory=lambda: {"primary": "#3b82f6", "dark": True})
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SpecEngine:
    SYSTEM_PROMPT = """You are an expert full-stack software architect specializing in v2.0 spec-driven application generation.
Convert the user's app idea into a rich, production-grade JSON AppSpec.

Rules:
- Generate REAL models with proper fields (not demo data). Include realistic relationships between models.
- Include auth (auth=true) if the app has users, profiles, roles, or multi-tenancy.
- Specify business_rules for critical domain logic (e.g. checking stock before create, sending emails on order status change, inventory deduction).
- Specify workflows (state machines) for lifecycle fields (e.g. status transition from pending -> processing -> shipped -> delivered).
- Specify background_jobs for asynchronous or scheduled processes (e.g. monthly reports, cleanup, automated alerts).
- Specify real_time_events for live updates (e.g. order created, stock low, notifications).
- Specify reports for analytics (line charts, bar charts, KPI cards) with aggregations.
- Default database to "postgresql". Set audit_log=true, soft_delete=true, and rbac=true for production apps.
- Include search/filter/pagination for list views, detail views, forms, and dashboard pages.

Output ONLY valid JSON matching the AppSpec schema."""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def generate(self, prompt: str) -> AppSpec:
        try:
            if self.llm and hasattr(self.llm, "complete"):
                response = await self.llm.complete(
                    [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": f"Create a production full-stack app spec for: {prompt}"}
                    ],
                    response_format={"type": "json_object"}
                )
                spec_dict = json.loads(response) if isinstance(response, str) else response
            else:
                spec_dict = await call_ai_json(self.SYSTEM_PROMPT, f"Create a production full-stack app spec for: {prompt}")

            return AppSpec(**spec_dict)
        except Exception as e:
            # Fallback deterministic AppSpec generator
            import re
            clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', prompt).strip().title()
            app_name = clean_name[:30] or "Real Production App"
            
            return AppSpec(
                name=app_name,
                description=prompt[:150],
                stack="react_fastapi",
                auth=True,
                auth_methods=["email"],
                database="postgresql",
                models=[
                    ModelSpec(
                        name="Item",
                        fields=[
                            FieldSpec(name="title", type="string", required=True),
                            FieldSpec(name="description", type="text", required=False),
                            FieldSpec(name="status", type="string", default="pending"),
                            FieldSpec(name="amount", type="number", default="0.0")
                        ],
                        auth_required=True,
                        crud=["create", "read", "update", "delete", "search", "export"]
                    ),
                    ModelSpec(
                        name="Activity",
                        fields=[
                            FieldSpec(name="action", type="string", required=True),
                            FieldSpec(name="details", type="text", required=False)
                        ],
                        auth_required=True,
                        crud=["create", "read", "search"]
                    )
                ],
                pages=[
                    PageSpec(route="/", title="Dashboard", type="dashboard", layout="sidebar"),
                    PageSpec(route="/items", title="Items", type="list", model="Item", layout="sidebar"),
                    PageSpec(route="/activities", title="Activities", type="list", model="Activity", layout="sidebar")
                ],
                business_rules=[
                    BusinessRule(
                        name="Validate Amount",
                        trigger="before_create",
                        condition="amount < 0",
                        action="raise error Insufficient amount",
                        affected_models=["Item"]
                    )
                ],
                workflows=[
                    WorkflowSpec(
                        model="Item",
                        field="status",
                        states=[
                            WorkflowState(name="pending", transitions=[{"to": "active", "trigger": "activate"}]),
                            WorkflowState(name="active", transitions=[{"to": "completed", "trigger": "complete"}])
                        ],
                        initial_state="pending"
                    )
                ],
                background_jobs=[
                    JobSpec(name="Monthly Report", schedule="0 0 1 * *", handler="generate_monthly_report", queue="default")
                ],
                real_time_events=[
                    EventSpec(name="item.created", trigger_model="Item", trigger_action="create", broadcast_to=["admins"], payload_fields=["id", "title"])
                ],
                reports=[
                    ReportSpec(name="Item Growth", type="line_chart", data_source="Item", aggregations=[{"field": "id", "function": "count", "alias": "total"}])
                ],
                multi_tenant=True,
                audit_log=True,
                soft_delete=True,
                rbac=True
            )


