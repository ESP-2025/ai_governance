from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict
from ...core.security import verify_api_key
from ...models.schemas import AlertCreate

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.post("/")
async def create_alert(
    alert: AlertCreate,
    api_key: str = Depends(verify_api_key)
):
    """
    Log a compliance alert from the extension.
    """
    # In a real system, this would save to the database.
    # For now, we'll just log it to the console/stdout so it's visible.
    # Enforce default email if not provided
    if not alert.user_email:
        alert.user_email = "joshini.mn@gmail.com"

    print(f"ALERTS: Received alert from {alert.user_email}: {alert.violation_type}")
    print(f"DETAILS: {alert.details}")
    
    return {"status": "success", "message": "Alert logged"}
