import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from database import (
    init_db, check_date_conflict, create_booking, 
    get_all_bookings, get_confirmed_date_ranges, 
    update_booking_status, delete_booking, get_booking_by_id
)
from notifications import notify_owner_new_booking

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

app = FastAPI(
    title="Blue Heaven Farmhouse Booking API",
    description="Backend API for managing guest reservations & availability",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on Startup
@app.on_event("startup")
def on_startup():
    init_db()

# Mount items directory for static image serving
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(BASE_DIR, "items")
if os.path.exists(ITEMS_DIR):
    app.mount("/items", StaticFiles(directory=ITEMS_DIR), name="items")

# Request Models
class BookingCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    phone: str = Field(..., min_length=5)
    check_in: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    check_out: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    guests: int = Field(..., ge=1, le=100)
    package: str = Field(..., min_length=1)
    special_requests: Optional[str] = ""

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern=r"^(pending|confirmed|cancelled)$")

class AdminVerifyRequest(BaseModel):
    password: str

# Helper for Admin Authentication
def verify_admin_auth(x_admin_password: Optional[str] = Header(None)):
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    return True

# --- PUBLIC ENDPOINTS ---

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/admin")
def serve_admin():
    return FileResponse(os.path.join(BASE_DIR, "admin.html"))

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Blue Heaven Farmhouse API"}

@app.get("/api/availability")
def get_availability():
    """Returns confirmed booked date ranges so client can disable them."""
    confirmed = get_confirmed_date_ranges()
    return {"confirmed_ranges": confirmed}

@app.post("/api/bookings", status_code=status.HTTP_201_CREATED)
def submit_booking(payload: BookingCreateRequest):
    # 1. Validate dates
    try:
        cin = datetime.strptime(payload.check_in, "%Y-%m-%d").date()
        cout = datetime.strptime(payload.check_out, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    if cout <= cin:
        raise HTTPException(
            status_code=400, 
            detail="Check-out date must be after check-in date."
        )
    
    # 2. Check for date conflict with confirmed bookings
    if check_date_conflict(payload.check_in, payload.check_out):
        raise HTTPException(
            status_code= status.HTTP_409_CONFLICT,
            detail="The requested dates overlap with an existing confirmed booking. Please select different dates."
        )
    
    # 3. Store booking
    booking = create_booking(payload.dict())
    
    # 4. Notify Owner
    try:
        notify_owner_new_booking(booking)
    except Exception as e:
        print(f"Error sending owner notification: {e}")
        
    return {
        "success": True,
        "message": "Booking request submitted successfully! We will contact you shortly to confirm.",
        "booking": booking
    }

# --- ADMIN ENDPOINTS ---

@app.post("/api/admin/verify")
def verify_admin(payload: AdminVerifyRequest):
    if payload.password == ADMIN_PASSWORD:
        return {"success": True, "token": ADMIN_PASSWORD}
    raise HTTPException(status_code=401, detail="Invalid password")

@app.get("/api/admin/bookings")
def list_admin_bookings(auth: bool = Depends(verify_admin_auth)):
    bookings = get_all_bookings()
    return {"bookings": bookings}

@app.patch("/api/admin/bookings/{booking_id}/status")
def change_booking_status(
    booking_id: int, 
    payload: StatusUpdateRequest, 
    auth: bool = Depends(verify_admin_auth)
):
    existing = get_booking_by_id(booking_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    try:
        updated = update_booking_status(booking_id, payload.status)
        return {"success": True, "booking": updated}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.delete("/api/admin/bookings/{booking_id}")
def remove_booking(booking_id: int, auth: bool = Depends(verify_admin_auth)):
    success = delete_booking(booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"success": True, "message": "Booking deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
