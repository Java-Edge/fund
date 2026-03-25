from pydantic import BaseModel, Field


class AuthApplyRequest(BaseModel):
    socialType: str = Field(min_length=1)
    socialId: str = Field(min_length=1)
    password: str = ""
    nickname: str = "未命名"
    applyReason: str = ""


class AuthLoginRequest(BaseModel):
    socialType: str = Field(min_length=1)
    socialId: str = Field(min_length=1)
    password: str = ""


class AuthStatusQuery(BaseModel):
    socialType: str = Field(min_length=1)
    socialId: str = Field(min_length=1)


class AuthReviewRequest(BaseModel):
    userId: str = Field(min_length=1)
    action: str = Field(min_length=1)
    note: str = ""
