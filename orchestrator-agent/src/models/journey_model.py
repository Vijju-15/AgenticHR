"""MongoDB document models for structured onboarding journeys."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class JourneyStepStatus(str, Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    SKIPPED     = "SKIPPED"


# Default 3-day onboarding plan --------------------------------------------

DEFAULT_JOURNEY_PLAN: List[Dict[str, Any]] = [
    # ── Day 1 ──────────────────────────────────────────────────────────────
    {
        "day": 1,
        "title": "Welcome & Orientation",
        "steps": [
            {
                "step_id":     "d1_hr_intro",
                "title":       "HR Introduction Meeting",
                "description": "Meet the HR team, receive your welcome kit and ID card.",
                "type":        "meeting",
                "status":      "PENDING",
                "meeting_type":"hr_session",
                "duration_min": 45,
            },
            {
                "step_id":      "d1_policy_overview",
                "title":        "Company Policy Overview",
                "description":  "Review company policies: leave, code of conduct, benefits.",
                "type":         "document",
                "status":       "PENDING",
                "resource_url": "",
            },
            {
                "step_id":     "d1_doc_submission",
                "title":       "Document Submission",
                "description": "Submit your joining documents and ID proof.",
                "type":        "task",
                "status":      "PENDING",
            },
        ]
    },
    # ── Day 2 ──────────────────────────────────────────────────────────────
    {
        "day": 2,
        "title": "Team Integration",
        "steps": [
            {
                "step_id":      "d2_manager_intro",
                "title":        "Manager Introduction",
                "description":  "1-on-1 with your reporting manager.",
                "type":         "meeting",
                "status":       "PENDING",
                "meeting_type": "manager_intro",
                "duration_min": 30,
            },
            {
                "step_id":      "d2_team_welcome",
                "title":        "Team Welcome Meeting",
                "description":  "Meet your direct teammates.",
                "type":         "meeting",
                "status":       "PENDING",
                "meeting_type": "induction",
                "duration_min": 60,
            },
            {
                "step_id":      "d2_tool_access",
                "title":        "Tool Access Instructions",
                "description":  "Set up your email, Slack, Jira and other tools.",
                "type":         "task",
                "status":       "PENDING",
            },
        ]
    },
    # ── Day 3 ──────────────────────────────────────────────────────────────
    {
        "day": 3,
        "title": "Work Orientation",
        "steps": [
            {
                "step_id":      "d3_training",
                "title":        "Training Session",
                "description":  "Attend the mandatory onboarding training.",
                "type":         "meeting",
                "status":       "PENDING",
                "meeting_type": "hr_session",
                "duration_min": 90,
            },
            {
                "step_id":     "d3_project_overview",
                "title":       "Project Overview",
                "description": "Your manager walks you through current projects.",
                "type":        "task",
                "status":      "PENDING",
            },
            {
                "step_id":     "d3_first_assignment",
                "title":       "First Assignment Orientation",
                "description": "Receive and review your first task / assignment.",
                "type":        "task",
                "status":      "PENDING",
            },
        ]
    },
]


def journey_to_dict(
    journey_id: str,
    tenant_id: str,
    employee_id: str,
    employee_name: str,
    employee_email: str,
    start_date: str,
    plan: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an onboarding journey document."""
    import copy
    now = datetime.now(timezone.utc)
    return {
        "journey_id":     journey_id,
        "tenant_id":      tenant_id,
        "employee_id":    employee_id,
        "employee_name":  employee_name,
        "employee_email": employee_email,
        "start_date":     start_date,
        "plan":           copy.deepcopy(plan or DEFAULT_JOURNEY_PLAN),
        "current_day":    1,
        "overall_progress_pct": 0,
        "created_at":     now,
        "updated_at":     now,
        "completed_at":   None,
        "metadata":       metadata or {},
    }


def _calc_progress(plan: List[Dict[str, Any]]) -> int:
    """Calculate overall progress as integer percentage."""
    total = sum(len(day["steps"]) for day in plan)
    done  = sum(
        1
        for day in plan
        for step in day["steps"]
        if step["status"] in ("COMPLETED", "SKIPPED")
    )
    return int(done / total * 100) if total else 0
