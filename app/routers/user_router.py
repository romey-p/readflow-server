from fastapi import APIRouter, HTTPException
from app.schemas.user_schema import UserSignupRequest, UserSignupResponse, UserLoginRequest, UserLoginResponse
from app.services.user_service import create_user, authenticate_user, create_access_token

router = APIRouter(prefix="/api", tags=["Users"])

@router.post("/users", response_model=UserSignupResponse)
def signup(payload: UserSignupRequest):
    try:
        user = create_user(payload.email, payload.password)
        return {
            "success": True,
            "user_id": user["user_id"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/auth/login", response_model=UserLoginResponse)
def login(payload: UserLoginRequest):
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    
    token = create_access_token()
    
    return {
        "success": True,
        "user_id": user["user_id"],
        "email": user["email"],
        "access_token": token
    }
