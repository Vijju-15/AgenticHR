"""Seed default demo users into MongoDB for AgenticHR."""
from pymongo import MongoClient
import bcrypt

def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

c = MongoClient("mongodb://localhost:27017")
db = c["agentichr"]

users = [
    {
        "user_id": "hr_admin_001",
        "tenant_id": "acme_corp",
        "email": "hr@acme.com",
        "full_name": "HR Admin",
        "role": "hr",
        "department": "Human Resources",
        "password_hash": _hash("HR@acme123"),
    },
    {
        "user_id": "intern_001",
        "tenant_id": "acme_corp",
        "email": "intern@acme.com",
        "full_name": "Alex Johnson",
        "role": "employee",
        "department": "Engineering",
        "password_hash": _hash("Intern@acme123"),
    },
]

for u in users:
    db.users.update_one({"user_id": u["user_id"]}, {"$set": u}, upsert=True)
    print(f"Seeded: {u['email']} / {u['role']}")

db.users.create_index([("tenant_id", 1), ("email", 1)], unique=True, background=True)
print(f"Total users: {db.users.count_documents({})}")
