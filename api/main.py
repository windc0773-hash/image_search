from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import time
import os

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
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "智能图片搜索引擎 API", "docs": "/docs"}

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


@app.get("/api/v1/stats")
async def get_stats():
    """获取搜索统计信息"""
    try:
        from es_manager.index_manager import IndexManager
        mgr = IndexManager()
        
        # 获取图片总数
        image_count = mgr.count_documents()
        
        # 获取所有标签
        tags_result = mgr.get_all_tags()
        tags = tags_result.get("tags", [])
        
        # 计算平均评分
        avg_score_result = mgr.get_average_score()
        avg_score = avg_score_result.get("avg_score", 0)
        
        # 获取最后更新时间
        last_update = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return ApiResponse(data={
            "total_images": image_count,
            "total_tags": len(tags),
            "popular_tags": tags[:10],
            "avg_score": round(avg_score, 2),
            "last_update": last_update
        })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息异常: {str(e)}"
        )


@app.post("/api/v1/images/search", response_model=SearchResponse)
async def search_images(req: SearchRequest):
    start_time = time.time()

    try:
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索服务异常: {str(e)}"
        )


@app.get("/api/v1/images/{image_id}")
async def get_image(image_id: str):
    try:
        from data_sync.sync import get_image as _get_image
        resp = _get_image(image_id)
        if not resp.get("found"):
            raise HTTPException(status_code=404, detail="图片不存在")
        return ApiResponse(data=resp["_source"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取图片异常: {str(e)}"
        )


@app.post("/api/v1/images/upsert")
async def upsert_image_api(req: ImageUpsertRequest):
    try:
        doc = req.model_dump(exclude_none=True)
        upsert_image(doc)
        return ApiResponse(message="图片写入成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"图片写入异常: {str(e)}"
        )


@app.delete("/api/v1/images/{image_id}")
async def delete_image(image_id: str):
    try:
        from data_sync.sync import delete_image as _delete
        _delete(image_id)
        return ApiResponse(message="图片删除成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"图片删除异常: {str(e)}"
        )


@app.get("/api/v1/tags/suggest")
async def suggest_tags(prefix: str = Query(..., description="标签前缀")):
    try:
        tags = searcher.suggest(prefix)
        return ApiResponse(data={"tags": tags})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"标签建议异常: {str(e)}"
        )


@app.post("/api/v1/synonyms")
async def add_synonym_api(req: SynonymAddRequest):
    try:
        add_synonym(req.word, req.synonyms)
        return ApiResponse(message="同义词添加成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"同义词添加异常: {str(e)}"
        )


@app.post("/api/v1/init-index")
async def init_index():
    try:
        from es_manager.index_manager import IndexManager
        mgr = IndexManager()
        mgr.init_image_index()
        mgr.init_synonym_index()
        return ApiResponse(message="索引初始化成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"索引初始化异常: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
