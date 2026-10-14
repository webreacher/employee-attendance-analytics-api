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

**Live Interactive API Documentation:**  
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

It serves three main purposes:

Visual Endpoint Reference:
It lists every available route (GET, POST, PUT, DELETE), expected parameters, required request body schemas, and possible HTTP status response codes (like 200, 201, 404, 422).

Built-in API Testing (Without Postman or Curl):
It allows you to test endpoints directly in your browser. By clicking Try it out, entering sample JSON payloads, and clicking Execute, you send live HTTP requests to your running FastAPI backend and view the actual responses in real time.

Live Schema Validation:
It reads your Pydantic models (like PunchRequest and EmployeeCreate) to show exact JSON structures, data types, and required fields. If invalid data is submitted, it shows the validation errors immediately.
