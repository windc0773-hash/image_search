from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class SearchMode(str, Enum):
    """搜索模式"""
    TEXT = "text"           # 纯文本搜索
    IMAGE = "image"         # 纯图像搜索
    HYBRID = "hybrid"       # 混合搜索（文本+图像）


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
    query: Optional[str] = Field(None, description="搜索关键词，文本搜索时必填")
    query_image: Optional[str] = Field(None, description="Base64编码的图片数据，图像搜索时必填")
    query_image_url: Optional[str] = Field(None, description="图片URL，可以作为query_image的替代")
    mode: SearchMode = Field(SearchMode.TEXT, description="搜索模式")
    filters: Optional[SearchFilters] = None
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")
    sort: str = Field("relevance", description="排序方式: relevance/popularity/time")
    highlight: bool = Field(True, description="是否高亮（仅文本搜索有效）")
    search_fields: Optional[List[str]] = Field(
        default=None,
        description="搜索字段及权重，如 ['title^3', 'tags^2']（仅文本搜索有效）"
    )
    hybrid_weight: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="混合搜索中图像搜索的权重")
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    width_min: Optional[int] = None
    width_max: Optional[int] = None
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    create_time_start: Optional[str] = None
    create_time_end: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "hybrid",
                "query": "可爱的小猫",
                "query_image_url": "https://example.com/cat.jpg",
                "hybrid_weight": 0.6,
                "page": 1,
                "size": 20
            }
        }


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


class MultimodalSearchResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None
    search_mode: str
    query_info: Optional[dict] = None
