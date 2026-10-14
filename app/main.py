import os
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from bson import ObjectId

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING, DESCENDING

# ---------------------------------------------------------
# App Initialization & MongoDB Setup
# ---------------------------------------------------------
app = FastAPI(
    title="Employee Attendance & Analytics API",
    version="1.0.0",
    description="Attendance tracking, audit trails, and MongoDB analytics pipelines."
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "attendance_analytics_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
employees_col = db["employees"]
attendance_col = db["attendance"]
audit_col = db["audit_logs"]

# Ensure essential indexes
employees_col.create_index([("employee_id", ASCENDING)], unique=True)
attendance_col.create_index([("employee_id", ASCENDING), ("date", ASCENDING)], unique=True)
audit_col.create_index([("attendance_id", ASCENDING)])


# ---------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------
def round_half_up(value: float, decimals: int = 4) -> float:
    if value is None:
        return None
    d = Decimal(str(value))
    return float(d.quantize(Decimal("1." + "0" * decimals), rounding=ROUND_HALF_UP))


def parse_date(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
        )


# ---------------------------------------------------------
# Schemas
# ---------------------------------------------------------
class EmployeeCreate(BaseModel):
    employee_id: str = Field(..., example="EMP001")
    name: str = Field(..., example="Jane Doe")
    department: str = Field(..., example="Engineering")
    is_active: bool = True


class PunchRequest(BaseModel):
    employee_id: str = Field(..., example="EMP001")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttendanceCorrectionRequest(BaseModel):
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    reason: str = Field(..., min_length=5, example="System outage during punch-in")
    modified_by: str = Field(..., example="HR_ADMIN")


# ---------------------------------------------------------
# Aggregation Pipeline Builders
# ---------------------------------------------------------
def build_department_trend_pipeline(department: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    return [
        {
            "$match": {
                "department": department,
                "date": {"$gte": from_date, "$lte": to_date}
            }
        },
        {
            "$project": {
                "date": 1,
                "department": 1,
                "total_hours": 1,
                "attendance_rate": {
                    "$cond": [
                        {"$gte": ["$total_hours", 8.0]},
                        1.0,
                        {"$divide": ["$total_hours", 8.0]}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$date",
                "attendance_rate": {"$avg": "$attendance_rate"}
            }
        },
        {"$sort": {"_id": 1}},
        {
            "$setWindowFields": {
                "sortBy": {"_id": 1},
                "output": {
                    "moving_avg_7d": {
                        "$avg": "$attendance_rate",
                        "window": {"documents": [-6, 0]}
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "date": "$_id",
                "attendance_rate": 1,
                "moving_avg_7d": 1
            }
        },
        {"$sort": {"date": 1}}
    ]


# ---------------------------------------------------------
# Employee Endpoints
# ---------------------------------------------------------
@app.post("/employees", status_code=status.HTTP_201_CREATED)
def create_employee(emp: EmployeeCreate):
    if employees_col.find_one({"employee_id": emp.employee_id}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee ID already exists")
    
    doc = emp.model_dump()
    employees_col.insert_one(doc)
    return {"message": "Employee created successfully", "employee_id": emp.employee_id}


# ---------------------------------------------------------
# Attendance Endpoints (Punch-in / Punch-out)
# ---------------------------------------------------------
@app.post("/attendance/punch-in", status_code=status.HTTP_200_OK)
def punch_in(req: PunchRequest):
    emp = employees_col.find_one({"employee_id": req.employee_id})
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    date_str = req.timestamp.strftime("%Y-%m-%d")
    record = attendance_col.find_one({"employee_id": req.employee_id, "date": date_str})

    if record and record.get("punch_in"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee has already punched in for today"
        )

    if not record:
        new_record = {
            "employee_id": req.employee_id,
            "department": emp.get("department"),
            "date": date_str,
            "punch_in": req.timestamp,
            "punch_out": None,
            "total_hours": 0.0,
            "status": "IN_PROGRESS"
        }
        res = attendance_col.insert_one(new_record)
        return {"message": "Punch-in registered", "id": str(res.inserted_id)}
    else:
        attendance_col.update_one(
            {"_id": record["_id"]},
            {"$set": {"punch_in": req.timestamp}}
        )
        return {"message": "Punch-in updated", "id": str(record["_id"])}


@app.post("/attendance/punch-out", status_code=status.HTTP_200_OK)
def punch_out(req: PunchRequest):
    date_str = req.timestamp.strftime("%Y-%m-%d")
    record = attendance_col.find_one({"employee_id": req.employee_id, "date": date_str})

    if not record or not record.get("punch_in"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot punch out without an active punch-in for today"
        )

    punch_in_time = record["punch_in"]
    if req.timestamp <= punch_in_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Punch-out timestamp must be after punch-in timestamp"
        )

    duration_seconds = (req.timestamp - punch_in_time).total_seconds()
    total_hours = round(duration_seconds / 3600.0, 2)

    attendance_col.update_one(
        {"_id": record["_id"]},
        {"$set": {
            "punch_out": req.timestamp,
            "total_hours": total_hours,
            "status": "COMPLETED"
        }}
    )
    return {"message": "Punch-out registered", "total_hours": total_hours}


# ---------------------------------------------------------
# Audit & Manual Corrections
# ---------------------------------------------------------
@app.put("/attendance/{record_id}/correct", status_code=status.HTTP_200_OK)
def correct_attendance(record_id: str, correction: AttendanceCorrectionRequest):
    try:
        obj_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid record ID")

    record = attendance_col.find_one({"_id": obj_id})
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    new_in = correction.punch_in or record.get("punch_in")
    new_out = correction.punch_out or record.get("punch_out")

    if new_in and new_out and new_out <= new_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="punch_out must be strictly greater than punch_in"
        )

    total_hours = 0.0
    if new_in and new_out:
        total_hours = round((new_out - new_in).total_seconds() / 3600.0, 2)

    # Save to Audit Log Collection
    audit_entry = {
        "attendance_id": obj_id,
        "employee_id": record["employee_id"],
        "date": record["date"],
        "previous_state": {
            "punch_in": record.get("punch_in"),
            "punch_out": record.get("punch_out"),
            "total_hours": record.get("total_hours")
        },
        "updated_state": {
            "punch_in": new_in,
            "punch_out": new_out,
            "total_hours": total_hours
        },
        "reason": correction.reason,
        "modified_by": correction.modified_by,
        "modified_at": datetime.utcnow()
    }
    audit_col.insert_one(audit_entry)

    # Apply Update
    attendance_col.update_one(
        {"_id": obj_id},
        {"$set": {
            "punch_in": new_in,
            "punch_out": new_out,
            "total_hours": total_hours,
            "corrected": True
        }}
    )

    return {"message": "Attendance record updated with audit log preserved", "total_hours": total_hours}


# ---------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------
@app.get("/analytics/department-trend")
def get_department_trend(
    department: str = Query(..., description="Department name"),
    from_date: str = Query(..., alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="End date (YYYY-MM-DD)")
):
    d_from = parse_date(from_date)
    d_to = parse_date(to_date)

    if d_to < d_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' date must be >= 'from' date"
        )

    if (d_to - d_from).days > 92:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Date range cannot exceed 92 days"
        )

    dept_exists = employees_col.find_one({"department": department})
    if not dept_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    pipeline = build_department_trend_pipeline(department, from_date, to_date)
    raw_items = list(attendance_col.aggregate(pipeline))

    items = []
    for r in raw_items:
        rate = round_half_up(r.get("attendance_rate"), 4) if r.get("attendance_rate") is not None else None
        m_avg = round_half_up(r.get("moving_avg_7d"), 4) if r.get("moving_avg_7d") is not None else None
        items.append({
            "date": r["date"],
            "attendance_rate": rate,
            "moving_avg_7d": m_avg
        })

    return {
        "department": department,
        "from": from_date,
        "to": to_date,
        "trend": items
    }