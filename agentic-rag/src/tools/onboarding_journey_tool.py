"""Onboarding Journey Tools for Guide Agent.

These tools allow the Guide Agent to:
1. Retrieve an employee's onboarding journey progress
2. Mark onboarding steps as completed
3. Get the next pending steps / suggest what to do next

The Guide Agent uses these tools to act as an AI-powered onboarding companion.
"""

from __future__ import annotations

import os
import httpx
from loguru import logger

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_AGENT_URL", "http://localhost:8001")
_TIMEOUT = 10


def get_onboarding_progress(employee_id: str, company_id: str) -> str:
    """
    Get the structured onboarding journey progress for an employee.

    Use this tool when an employee asks about:
    - Their onboarding tasks / checklist
    - What they should do next
    - Their onboarding progress
    - How far along they are in the onboarding process
    - What meetings are scheduled during onboarding

    Args:
        employee_id: Employee's ID
        company_id:  Company / tenant identifier

    Returns:
        Formatted onboarding journey with progress and next steps
    """
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{ORCHESTRATOR_URL}/onboarding/journey/{employee_id}",
                params={"tenant_id": company_id},
            )
            if resp.status_code == 404:
                return (
                    f"No structured onboarding journey found for employee {employee_id}. "
                    f"Please ask your HR team to initialize your onboarding plan."
                )
            resp.raise_for_status()
            data = resp.json()

        employee_name = data.get("employee_name", employee_id)
        start_date    = data.get("start_date", "N/A")
        progress      = data.get("overall_progress_pct", 0)
        current_day   = data.get("current_day", 1)
        plan          = data.get("plan", [])

        bar_filled = int(progress / 10)
        progress_bar = "█" * bar_filled + "░" * (10 - bar_filled)

        lines = [
            f"🗺️  Onboarding Journey: {employee_name}",
            f"   Start Date  : {start_date}",
            f"   Progress    : [{progress_bar}] {progress}%",
            f"   Current Day : Day {current_day}",
            "",
        ]

        for day in plan:
            day_num   = day["day"]
            day_title = day["title"]
            steps     = day["steps"]
            done_ct   = sum(1 for s in steps if s["status"] in ("COMPLETED", "SKIPPED"))
            total_ct  = len(steps)
            day_icon  = "✅" if done_ct == total_ct else ("🔵" if day_num == current_day else "⚪")

            lines.append(f"  {day_icon} Day {day_num}: {day_title} ({done_ct}/{total_ct} done)")
            for step in steps:
                s_icon = {"COMPLETED": "  ✅", "SKIPPED": "  ⏭️", "IN_PROGRESS": "  🔄", "PENDING": "  ⬜"}.get(step["status"], "  •")
                lines.append(f"     {s_icon} {step['title']}")
                if step["status"] == "PENDING" and step.get("description"):
                    lines.append(f"          → {step['description']}")
            lines.append("")

        # Next step suggestion
        next_steps = [
            step
            for day in plan
            for step in day["steps"]
            if step["status"] == "PENDING"
        ]
        if next_steps:
            ns = next_steps[0]
            lines.append(f"💡 Next Step: {ns['title']}")
            lines.append(f"   {ns.get('description', '')}")
        else:
            lines.append("🎉 Congratulations! You have completed your onboarding journey!")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error fetching onboarding progress: {e}")
        return f"Could not fetch onboarding journey. Error: {str(e)}"


def complete_onboarding_step(employee_id: str, company_id: str, step_id: str) -> str:
    """
    Mark a specific onboarding step as completed for an employee.

    Use this when an employee confirms they have completed a task or attended a meeting.

    Args:
        employee_id: Employee's ID
        company_id:  Company / tenant identifier
        step_id:     The step ID to mark as completed (e.g. "d1_hr_intro")

    Returns:
        Confirmation message with updated progress
    """
    try:
        payload = {"step_id": step_id, "status": "COMPLETED"}
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{ORCHESTRATOR_URL}/onboarding/journey/{employee_id}/complete-step",
                params={"tenant_id": company_id},
                json=payload,
            )
            if resp.status_code == 404:
                return f"Step '{step_id}' not found in onboarding journey."
            resp.raise_for_status()
            data = resp.json()

        progress = data.get("progress_pct", 0)
        return (
            f"✅ Onboarding step '{step_id}' marked as COMPLETED!\n"
            f"   Overall Progress: {progress}%\n"
            f"   Keep up the great work!"
        )
    except Exception as e:
        logger.error(f"Error completing onboarding step: {e}")
        return f"Could not update onboarding step. Error: {str(e)}"
