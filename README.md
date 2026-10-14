# Employee Attendance & Analytics API

FastAPI & MongoDB service for tracking employee punch-in/out records, performing audited manual adjustments, and computing multi-day department attendance trends.

## Setup & Running

1. **Activate your virtual environment:**
   ```powershell
   .venv\Scripts\Activate.ps1

   # Employee Attendance & Analytics API

A RESTful service built with FastAPI and MongoDB that handles employee attendance tracking, manual corrections with an immutable audit trail, and department analytics using MongoDB aggregation pipelines.

---

## 🛠 Tech Stack

- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Database:** MongoDB
- **Driver:** PyMongo
- **Data Validation:** Pydantic v2
- **Testing & Docs:** Swagger UI / OpenAPI 3.0

---

## 📁 Repository Structure

```text
├── app/
│   └── main.py          # FastAPI endpoints, validation, and aggregation pipelines
├── requirements.txt     # Python dependencies
├── DECISIONS.md         # Architectural decisions and rationale
├── REVIEW.md            # Code review and security/concurrency analysis
└── README.md            # System documentation and local setup
