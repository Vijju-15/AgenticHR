"""
Seed example emails into MongoDB for AgenticHR demo.

HR emails    → dashboard_target: "hr"       (visible on HR Dashboard inbox)
Intern emails → dashboard_target: "employee" (visible on Intern/Employee Dashboard inbox)

Usage:
  python seed_emails.py
"""
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

c = MongoClient("mongodb://localhost:27017")
db = c["agentichr"]
tenant_id = "acme_corp"

now = datetime.now(timezone.utc)


def _email(eid, from_name, from_email, to_email, subject, body,
           intent, dashboard_target, priority, hours_ago):
    return {
        "email_id":         eid,
        "tenant_id":        tenant_id,
        "from_name":        from_name,
        "from_email":       from_email,
        "to_email":         to_email,
        "subject":          subject,
        "body":             body,
        "intent":           intent,
        "dashboard_target": dashboard_target,   # "hr" | "employee"
        "priority":         priority,            # "high" | "medium" | "low"
        "status":           "unread",
        "received_at":      now - timedelta(hours=hours_ago),
    }


emails = [
    # ── Emails routed to HR Dashboard ─────────────────────────────────────
    _email(
        eid="em_hr_001",
        from_name="Sarah Mitchell",
        from_email="sarah.mitchell@acme.com",
        to_email="hr@acme.com",
        subject="New Hire Onboarding Request – Dev Team",
        body=(
            "Hi HR team,\n\n"
            "I'd like to initiate onboarding for Jordan Lee who is joining the Dev team "
            "as a Software Engineer on March 9. Please set up their accounts, access cards "
            "and assign the standard Day-1/Day-2/Day-3 journey.\n\n"
            "Best,\nSarah Mitchell\nEngineering Manager"
        ),
        intent="onboarding_request",
        dashboard_target="hr",
        priority="high",
        hours_ago=2,
    ),
    _email(
        eid="em_hr_002",
        from_name="Alex Johnson",
        from_email="intern@acme.com",
        to_email="hr@acme.com",
        subject="Leave Request – Annual Leave 10–12 March",
        body=(
            "Dear HR,\n\n"
            "I would like to apply for 3 days of annual leave from March 10 to March 12, 2026. "
            "I have ensured my deliverables are covered during my absence.\n\n"
            "Please approve at your earliest convenience.\n\n"
            "Regards,\nAlex Johnson (Intern – Engineering)"
        ),
        intent="leave_request",
        dashboard_target="hr",
        priority="medium",
        hours_ago=5,
    ),
    _email(
        eid="em_hr_003",
        from_name="IT Department",
        from_email="it@acme.com",
        to_email="hr@acme.com",
        subject="Pending Access Provisioning for 3 New Hires",
        body=(
            "Hi HR,\n\n"
            "We have 3 new hires whose access provisioning is still pending approval:\n"
            "1. Jordan Lee – Software Engineer\n"
            "2. Priya Sharma – Data Analyst\n"
            "3. Marcus Chen – Product Manager\n\n"
            "Please confirm role assignments so we can proceed with tool access setup.\n\n"
            "Thanks,\nIT Support Team"
        ),
        intent="provisioning_action",
        dashboard_target="hr",
        priority="high",
        hours_ago=8,
    ),
    _email(
        eid="em_hr_004",
        from_name="Legal & Compliance",
        from_email="legal@acme.com",
        to_email="hr@acme.com",
        subject="Policy Update – Remote Work Policy v3.2",
        body=(
            "Dear HR Team,\n\n"
            "Please find the updated Remote Work Policy v3.2, effective April 1, 2026. "
            "Key changes include:\n"
            "- Maximum 3 remote days per week for engineers\n"
            "- Mandatory in-office on Tuesdays\n"
            "- VPN required for all remote connections\n\n"
            "Please distribute to all employees and update the policy portal.\n\n"
            "Best,\nLegal & Compliance"
        ),
        intent="policy_update",
        dashboard_target="hr",
        priority="medium",
        hours_ago=24,
    ),
    _email(
        eid="em_hr_005",
        from_name="Finance Team",
        from_email="finance@acme.com",
        to_email="hr@acme.com",
        subject="Payroll Discrepancy – March 2026",
        body=(
            "Hi HR,\n\n"
            "We noticed a payroll discrepancy for two employees in the Engineering department. "
            "Overtime hours for Feb 25 – Mar 1 were not captured in the system.\n\n"
            "Could you please verify and approve the correction before the March 8 payroll run?\n\n"
            "Thanks,\nFinance"
        ),
        intent="hr_action",
        dashboard_target="hr",
        priority="high",
        hours_ago=36,
    ),

    # ── Emails routed to Employee / Intern Dashboard ───────────────────────
    _email(
        eid="em_emp_001",
        from_name="HR Admin",
        from_email="hr@acme.com",
        to_email="intern@acme.com",
        subject="Welcome to Acme Corp! Your Onboarding Starts Monday",
        body=(
            "Dear Alex,\n\n"
            "Welcome aboard! We're thrilled to have you join the Engineering team.\n\n"
            "Your onboarding begins Monday, March 9. Here's what to expect:\n"
            "• Day 1: HR Introduction, Policy Overview, Document Submission\n"
            "• Day 2: Manager 1-on-1, Team Welcome, Tool Access Setup\n"
            "• Day 3: Training Modules, Project Overview, First Assignment\n\n"
            "Please bring a valid photo ID and arrive by 9:00 AM at Reception.\n\n"
            "Looking forward to having you with us!\n\nBest,\nHR Team"
        ),
        intent="welcome_onboarding",
        dashboard_target="employee",
        priority="high",
        hours_ago=1,
    ),
    _email(
        eid="em_emp_002",
        from_name="IT Support",
        from_email="it@acme.com",
        to_email="intern@acme.com",
        subject="Your Acme Corp Login Credentials & Tool Access",
        body=(
            "Hi Alex,\n\n"
            "Your accounts have been set up. Here are your login details:\n\n"
            "• Corporate Email: alex.johnson@acme.com\n"
            "• Slack Workspace: acmecorp.slack.com (invite sent to personal email)\n"
            "• Jira: jira.acme.com (credentials emailed separately)\n"
            "• GitHub Org: github.com/acme-corp (invitation sent)\n"
            "• VPN: Download Cisco AnyConnect, server: vpn.acme.com\n\n"
            "Please change all temporary passwords on first login.\n\n"
            "IT Support"
        ),
        intent="tool_access",
        dashboard_target="employee",
        priority="high",
        hours_ago=3,
    ),
    _email(
        eid="em_emp_003",
        from_name="HR Admin",
        from_email="hr@acme.com",
        to_email="intern@acme.com",
        subject="Leave Request Approved – March 10–12",
        body=(
            "Hi Alex,\n\n"
            "Your leave request for March 10–12, 2026 (3 days annual leave) has been approved.\n\n"
            "Your leave balance has been updated accordingly. Please coordinate with your "
            "manager to ensure work continuity during your absence.\n\n"
            "Have a great break!\n\nBest,\nHR Team"
        ),
        intent="leave_approval",
        dashboard_target="employee",
        priority="medium",
        hours_ago=4,
    ),
    _email(
        eid="em_emp_004",
        from_name="Manager – Sarah Mitchell",
        from_email="sarah.mitchell@acme.com",
        to_email="intern@acme.com",
        subject="Your First Project Assignment",
        body=(
            "Hey Alex,\n\n"
            "Welcome to the team! I'm excited to have you on board.\n\n"
            "For your first assignment, you'll be working on the AgenticHR dashboard UI improvements. "
            "I'll walk you through the codebase in our Day-3 meeting.\n\n"
            "In the meantime, please:\n"
            "1. Clone the repo: github.com/acme-corp/agentichr\n"
            "2. Read the README and ARCHITECTURE docs\n"
            "3. Set up your local dev environment\n\n"
            "Drop me a message on Slack if you have questions!\n\nSarah"
        ),
        intent="first_assignment",
        dashboard_target="employee",
        priority="medium",
        hours_ago=6,
    ),
    _email(
        eid="em_emp_005",
        from_name="Benefits Team",
        from_email="benefits@acme.com",
        to_email="intern@acme.com",
        subject="Enroll in Your Benefits by March 15",
        body=(
            "Dear Alex,\n\n"
            "As a new Acme Corp employee, you're eligible to enroll in the following benefits:\n\n"
            "• Health Insurance (Medical, Dental, Vision)\n"
            "• Life Insurance (2x annual salary)\n"
            "• 401(k) with 4% employer match\n"
            "• Flexible Spending Account (FSA)\n"
            "• Employee Assistance Program (EAP)\n\n"
            "Please complete your enrollment at benefits.acme.com by March 15, 2026.\n\n"
            "Questions? Reply to this email or visit HR.\n\nBenefits Team"
        ),
        intent="benefits_enrollment",
        dashboard_target="employee",
        priority="medium",
        hours_ago=12,
    ),
    _email(
        eid="em_emp_006",
        from_name="Payroll",
        from_email="payroll@acme.com",
        to_email="intern@acme.com",
        subject="Action Required: Submit Bank Details for Payroll",
        body=(
            "Hi Alex,\n\n"
            "To process your first paycheck, we need your banking information.\n\n"
            "Please log in to the HR portal and navigate to Payroll > Direct Deposit "
            "to securely submit your details by March 12.\n\n"
            "Your first pay date is March 31, 2026.\n\n"
            "Regards,\nPayroll Department"
        ),
        intent="payroll_action",
        dashboard_target="employee",
        priority="high",
        hours_ago=18,
    ),
]

# Create indexes
db.emails.create_index("email_id", unique=True)
db.emails.create_index([("tenant_id", 1), ("dashboard_target", 1)])

inserted = 0
for em in emails:
    result = db.emails.update_one(
        {"email_id": em["email_id"]},
        {"$setOnInsert": em},
        upsert=True,
    )
    if result.upserted_id:
        inserted += 1
    print(f"  {'[NEW]' if result.upserted_id else '[EXISTS]'}  {em['dashboard_target']:9s}  {em['subject'][:55]}")

print(f"\nTotal in DB: {db.emails.count_documents({'tenant_id': tenant_id})}")
print(f"  HR emails:       {db.emails.count_documents({'tenant_id': tenant_id, 'dashboard_target': 'hr'})}")
print(f"  Employee emails: {db.emails.count_documents({'tenant_id': tenant_id, 'dashboard_target': 'employee'})}")
print(f"Newly inserted: {inserted}")
