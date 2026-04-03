from pydantic import BaseModel, Field
from typing import Optional, List


class SearchFilters(BaseModel):
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    width_min: Optional[int] = None
    width_max: Optional[int] = None
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    create_time_start: Optional[str] = None
    create_time_end: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="搜索关键词")
    filters: Optional[SearchFilters] = None
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")
    sort: str = Field("relevance", description="排序方式: relevance/popularity/time")
    highlight: bool = Field(True, description="是否高亮")
    search_fields: Optional[List[str]] = Field(
        default=None,
        description="搜索字段及权重，如 ['title^3', 'tags^2']"
    )
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    width_min: Optional[int] = None
    width_max: Optional[int] = None
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    create_time_start: Optional[str] = None
    create_time_end: Optional[str] = None


class ImageUpsertRequest(BaseModel):
    id: str
    url: str
    title: str
    tags: List[str]
    description: Optional[str] = None
    author: Optional[str] = None
    create_time: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    popularity: Optional[float] = None
    vector: Optional[List[float]] = None


class SynonymAddRequest(BaseModel):
    word: str
    synonyms: List[str]


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


class SearchResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None
