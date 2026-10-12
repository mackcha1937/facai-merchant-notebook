"""邀请内测认证契约。"""
from pydantic import BaseModel, Field, field_validator


class InviteRedeemRequest(BaseModel):
    invite_code: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    login_name: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("display_name", "login_name", "invite_code")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    login_name: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("login_name")
    @classmethod
    def normalize_login(cls, value: str) -> str:
        return value.strip().lower()


class AuthUserResponse(BaseModel):
    authenticated: bool = True
    auth_mode: str
    tenant_id: int
    tenant_slug: str
    tenant_name: str
    user_id: int
    display_name: str
    role: str
