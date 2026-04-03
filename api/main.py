from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time

from api.schemas import (
    SearchRequest, SearchFilters, ImageUpsertRequest,
    SynonymAddRequest, ApiResponse, SearchResponse
)
from search.searcher import ImageSearcher
from query_analyzer.analyzer import QueryAnalyzer
from data_sync.sync import upsert_image, add_synonym

app = FastAPI(
    title="智能图片搜索引擎",
    description="基于 Elasticsearch 的智能图片搜索服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

searcher = ImageSearcher()
analyzer = QueryAnalyzer()


@app.get("/health")
async def health_check():
    from es_manager.index_manager import IndexManager
    mgr = IndexManager()
    health = mgr.health_check()
    return {
        "status": "ok",
        "es_cluster_status": health["status"],
        "es_number_of_nodes": health["number_of_nodes"]
    }


@app.post("/api/v1/images/search", response_model=SearchResponse)
async def search_images(req: SearchRequest):
    start_time = time.time()

    analysis = analyzer.analyze(req.query)

    result = searcher.search(
        query=analysis["expanded"],
        filters=req.filters.model_dump() if req.filters else None,
        page=req.page,
        size=req.size,
        sort=req.sort,
        highlight=req.highlight,
        search_fields=req.search_fields
    )

    latency_ms = (time.time() - start_time) * 1000

    suggestions = []
    if analysis["has_correction"]:
        suggestions.append(analysis["corrected"])

    return SearchResponse(
        code=0,
        data={
            **result,
            "query_analysis": analysis,
            "suggestions": suggestions,
            "latency_ms": round(latency_ms, 2)
        }
    )


@app.get("/api/v1/images/{image_id}")
async def get_image(image_id: str):
    from data_sync.sync import get_image as _get_image
    resp = _get_image(image_id)
    if not resp.get("found"):
        raise HTTPException(status_code=404, detail="图片不存在")
    return ApiResponse(data=resp["_source"])


@app.post("/api/v1/images/upsert")
async def upsert_image_api(req: ImageUpsertRequest):
    doc = req.model_dump(exclude_none=True)
    try:
        upsert_image(doc)
        return ApiResponse(message="图片写入成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/images/{image_id}")
async def delete_image(image_id: str):
    from data_sync.sync import delete_image as _delete
    try:
        _delete(image_id)
        return ApiResponse(message="图片删除成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tags/suggest")
async def suggest_tags(prefix: str = Query(..., description="标签前缀")):
    tags = searcher.suggest(prefix)
    return ApiResponse(data={"tags": tags})


@app.post("/api/v1/synonyms")
async def add_synonym_api(req: SynonymAddRequest):
    try:
        add_synonym(req.word, req.synonyms)
        return ApiResponse(message="同义词添加成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/init-index")
async def init_index():
    from es_manager.index_manager import IndexManager
    mgr = IndexManager()
    try:
        mgr.init_image_index()
        mgr.init_synonym_index()
        return ApiResponse(message="索引初始化成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
