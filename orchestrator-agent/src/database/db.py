"""Database connection and session management for MongoDB."""

from pymongo import MongoClient
from pymongo.database import Database
from contextlib import contextmanager
from typing import Generator
from loguru import logger

from src.config.settings import settings


# Create MongoDB client
client = MongoClient(settings.mongodb_url)
db = client[settings.mongodb_db]


def init_db():
    """Initialize database - create indexes."""
    try:
        # Workflows
        db.workflows.create_index("workflow_id", unique=True)
        db.workflows.create_index("tenant_id")
        db.workflows.create_index("employee_id")
        db.workflows.create_index("status")

        # Tasks
        db.tasks.create_index("task_id", unique=True)
        db.tasks.create_index("workflow_id")
        db.tasks.create_index("tenant_id")
        db.tasks.create_index("status")

        # Leave requests
        db.leave_requests.create_index("request_id", unique=True)
        db.leave_requests.create_index("tenant_id")
        db.leave_requests.create_index("employee_id")
        db.leave_requests.create_index("status")

        # Onboarding journeys
        db.onboarding_journeys.create_index("journey_id", unique=True)
        db.onboarding_journeys.create_index("tenant_id")
        db.onboarding_journeys.create_index([("tenant_id", 1), ("employee_id", 1)])

        # Users / auth
        db.users.create_index("user_id", unique=True)
        db.users.create_index([("tenant_id", 1), ("email", 1)], unique=True)
        db.users.create_index("role")

        # Offer letters
        db.offer_letters.create_index("offer_id", unique=True)
        db.offer_letters.create_index("acceptance_token", unique=True)
        db.offer_letters.create_index("tenant_id")
        db.offer_letters.create_index("workflow_id")
        db.offer_letters.create_index("status")

        # Candidate documents
        db.candidate_documents.create_index("doc_id", unique=True)
        db.candidate_documents.create_index("tenant_id")
        db.candidate_documents.create_index("workflow_id")
        db.candidate_documents.create_index("employee_id")

        # Meetings (HR-scheduled meets with interns)
        db.meetings.create_index("meeting_id", unique=True)
        db.meetings.create_index("tenant_id")
        db.meetings.create_index("hr_email")
        db.meetings.create_index("intern_email")
        db.meetings.create_index([("tenant_id", 1), ("start_datetime", 1)])

        logger.info("MongoDB indexes created successfully")

        # Seed a default HR admin user if none exists
        _seed_default_users()

    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        # Don't raise - indexes might already exist


def _seed_default_users():
    """Insert default HR and Employee demo accounts if the users collection is empty."""
    try:
        from src.models.auth_model import hash_password, user_to_dict, UserRecord

        if db.users.count_documents({}) == 0:
            default_users = [
                # ── HR Users ──────────────────────────────────────────────────
                UserRecord(
                    user_id="hr_admin_001",
                    tenant_id="acme_corp",
                    email="hr@acme.com",
                    full_name="Priya Sharma",
                    role="hr",
                    department="Human Resources",
                    password_hash=hash_password("HR@acme123"),
                ),
                UserRecord(
                    user_id="hr_manager_002",
                    tenant_id="acme_corp",
                    email="hr.manager@acme.com",
                    full_name="Sarah Wilson",
                    role="hr",
                    department="Human Resources",
                    password_hash=hash_password("HR@acme123"),
                ),
                UserRecord(
                    user_id="hr_recruiter_003",
                    tenant_id="acme_corp",
                    email="recruiter@acme.com",
                    full_name="Michael Chen",
                    role="hr",
                    department="Human Resources",
                    password_hash=hash_password("HR@acme123"),
                ),
                # ── Intern / Employee Users ───────────────────────────────────
                UserRecord(
                    user_id="intern_001",
                    tenant_id="acme_corp",
                    email="intern@acme.com",
                    full_name="Alex Johnson",
                    role="employee",
                    department="Engineering",
                    password_hash=hash_password("Intern@acme123"),
                ),
                UserRecord(
                    user_id="intern_002",
                    tenant_id="acme_corp",
                    email="john.doe@acme.com",
                    full_name="John Doe",
                    role="employee",
                    department="Engineering",
                    password_hash=hash_password("Intern@acme123"),
                ),
                UserRecord(
                    user_id="intern_003",
                    tenant_id="acme_corp",
                    email="jane.smith@acme.com",
                    full_name="Jane Smith",
                    role="employee",
                    department="Design",
                    password_hash=hash_password("Intern@acme123"),
                ),
                UserRecord(
                    user_id="fresher_001",
                    tenant_id="acme_corp",
                    email="fresher@acme.com",
                    full_name="Emily Brown",
                    role="employee",
                    department="Marketing",
                    password_hash=hash_password("Intern@acme123"),
                ),
                UserRecord(
                    user_id="new_hire_001",
                    tenant_id="acme_corp",
                    email="newhire@acme.com",
                    full_name="David Lee",
                    role="employee",
                    department="Sales",
                    password_hash=hash_password("Intern@acme123"),
                ),
            ]
            for u in default_users:
                db.users.insert_one(user_to_dict(u))
            logger.info("Seeded 8 default demo users (3 HR, 5 employees)")

        # Always ensure personal_email field exists on employee users (upsert migration)
        personal_emails = {
            "intern@acme.com":   "alex.johnson.dev@gmail.com",
            "john.doe@acme.com": "johndoe.personal@gmail.com",
            "jane.smith@acme.com": "janesmith.designs@gmail.com",
            "fresher@acme.com":  "emily.brown99@gmail.com",
            "newhire@acme.com":  "david.lee.work@gmail.com",
        }
        for corp_email, personal_email in personal_emails.items():
            db.users.update_one(
                {"email": corp_email},
                {"$set": {"personal_email": personal_email}},
            )

    except Exception as e:
        logger.warning(f"Could not seed default users: {e}")


@contextmanager
def get_db() -> Generator[Database, None, None]:
    """Get database context manager."""
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


def get_db_session() -> Database:
    """Get database for FastAPI dependency injection."""
    return db
