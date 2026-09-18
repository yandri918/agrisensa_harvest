from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel
from enum import Enum

DataT = TypeVar("DataT")


class HarvestStatusEnum(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    SYNCED = "synced"
    ARCHIVED = "archived"


class DataSourceEnum(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    SHEETS = "sheets"
    API = "api"
    IMPORT = "import"


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "Success"
    data: Optional[DataT] = None
    errors: Optional[List[str]] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    items: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
