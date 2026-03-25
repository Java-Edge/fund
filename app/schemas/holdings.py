from typing import Any

from pydantic import BaseModel, Field


class HoldingUserQuery(BaseModel):
    userId: str = Field(min_length=1)


class HoldingCreateRequest(BaseModel):
    userId: str = Field(min_length=1)
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = "equity"
    shares: float | int = 0
    cost: float | int = 0
    accountId: str = "alipay"
    watchOnly: bool = False


class HoldingUpdateRequest(BaseModel):
    userId: str = Field(min_length=1)
    shares: float | int | None = None
    cost: float | int | None = None
    accountId: str | None = None
    watchOnly: bool | None = None

    def to_updates(self) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if self.shares is not None:
            updates["shares"] = self.shares
        if self.cost is not None:
            updates["cost_price"] = self.cost
        if self.accountId is not None:
            updates["account_id"] = self.accountId
        if self.watchOnly is not None:
            updates["watch_only"] = 1 if self.watchOnly else 0
        return updates


class HoldingBatchItem(BaseModel):
    code: str | None = None
    name: str | None = None
    type: str = "equity"
    shares: float | int = 0
    cost: float | int = 0
    accountId: str = "alipay"
    watchOnly: bool = False


class HoldingBatchCreateRequest(BaseModel):
    userId: str = Field(min_length=1)
    holdings: list[HoldingBatchItem] = Field(default_factory=list)
