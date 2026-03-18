from pydantic import BaseModel, Field, field_validator


class FundCodePath(BaseModel):
    fund_code: str

    @field_validator("fund_code")
    @classmethod
    def validate_fund_code(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise ValueError("基金代码必须为6位数字")
        return value


class FundBatchRequest(BaseModel):
    codes: list[str] = Field(default_factory=list)

    @field_validator("codes")
    @classmethod
    def validate_codes(cls, value: list[str]) -> list[str]:
        normalized = [str(v) for v in value]
        for code in normalized:
            if not code.isdigit() or len(code) != 6:
                raise ValueError("所有基金代码必须为6位数字")
        return normalized
