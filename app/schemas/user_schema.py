from pydantic import BaseModel, Field

class UserSignupRequest(BaseModel):
    email: str = Field(..., min_length=5, description="사용자 이메일")
    password: str = Field(..., min_length=4, description="비밀번호 (최소 4자)")

class UserSignupResponse(BaseModel):
    success: bool
    user_id: str

class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, description="사용자 이메일")
    password: str = Field(..., min_length=4, description="비밀번호")

class UserLoginResponse(BaseModel):
    success: bool
    user_id: str
    email: str
    access_token: str