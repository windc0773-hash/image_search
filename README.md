# 智能图片搜索引擎

基于 Elasticsearch 的智能图片搜索服务，支持全文检索、拼音搜索、同义词扩展、拼写纠错、向量召回（以图搜图）。

## 架构

```
客户端 → API Gateway → 图片搜索服务(FastAPI) → Elasticsearch 集群
                        ├─ 查询分析(纠错/同义词/拼音)
                        ├─ 多路加权召回 & 排序
                        └─ 结果高亮/分页/推荐
```

## 环境要求

- Python >= 3.9
- Elasticsearch >= 8.0（推荐 8.11+）
- ES 插件：`analysis-ik`（中文分词）、`analysis-pinyin`（拼音分词）

### 安装 ES 插件

```bash
# ik 中文分词（版本需与 ES 一致）
bin/elasticsearch-plugin install https://github.com/infinilabs/analysis-ik/releases/download/v8.11.0/elasticsearch-analysis-ik-8.11.0.zip

# pinyin 拼音分词
bin/elasticsearch-plugin install https://github.com/infinilabs/analysis-pinyin/releases/download/v8.11.0/elasticsearch-analysis-pinyin-8.11.0.zip

# 重启 ES
```

## 快速部署

```bash
# 1. 克隆项目
git clone <你的仓库地址>
cd image_search

# 2. 创建配置文件
cp .env.example .env
# 编辑 .env，修改 ES_HOST / ES_PASSWORD 等配置

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化 ES 索引
python -c "from es_manager.index_manager import IndexManager; m = IndexManager(); m.init_image_index(); m.init_synonym_index()"

# 5. 启动服务
python run.py
# 或：uvicorn api.main:app --host 0.0.0.0 --port 8000

# 6. 访问 API 文档
open http://localhost:8000/docs
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/images/search` | 智能图片搜索 |
| GET  | `/api/v1/images/{id}` | 获取图片详情 |
| POST | `/api/v1/images/upsert` | 上传/更新图片元数据 |
| DELETE| `/api/v1/images/{id}` | 删除图片 |
| GET  | `/api/v1/tags/suggest` | 标签联想推荐 |
| POST | `/api/v1/synonyms` | 添加同义词 |
| GET  | `/health` | 健康检查 |

### 搜索示例

```bash
curl -X POST http://localhost:8000/api/v1/images/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "红色跑车",
    "filters": {"tags": ["汽车"], "width_min": 1920},
    "page": 1,
    "size": 10,
    "sort": "relevance",
    "highlight": true,
    "search_fields": ["title^3", "tags^2", "description"]
  }'
```

### 上传图片元数据示例

```bash
curl -X POST http://localhost:8000/api/v1/images/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "id": "img_001",
    "url": "https://example.com/img.jpg",
    "title": "红色法拉利跑车",
    "tags": ["汽车", "红色", "跑车"],
    "description": "一辆红色法拉利停在赛道上",
    "author": "张三",
    "width": 3840,
    "height": 2160,
    "popularity": 9.5
  }'
```

## 目录结构

```
image_search/
├── config/settings.py       # 全局配置（ES连接、端口等）
├── es_manager/index_manager.py   # ES索引创建与管理
├── data_sync/sync.py        # 数据写入/CRUD/同义词管理
├── query_analyzer/analyzer.py    # 查询分析（纠错/同义词/拼音）
├── search/searcher.py       # 多路加权召回/过滤/排序/向量搜索
├── api/
│   ├── schemas.py           # Pydantic 请求/响应模型
│   └── main.py              # FastAPI 路由定义
├── run.py                   # 启动入口
├── .env.example             # 配置模板
├── .gitignore               # Git 忽略规则
└── requirements.txt         # Python 依赖
```

## 配置说明

环境变量（通过 `.env` 文件或系统环境变量设置）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ES_HOST` | `http://localhost:9200` | ES 地址 |
| `ES_USER` | `elastic` | ES 用户名 |
| `ES_PASSWORD` | `changeme` | ES 密码 |
| `ES_INDEX_NAME` | `image_index` | 图片索引名 |
| `API_PORT` | `8000` | API 服务端口 |

## 推送到远程仓库

```bash
git remote add origin <你的远程仓库地址>
git push -u origin main
```
