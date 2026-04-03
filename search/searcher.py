from elasticsearch import Elasticsearch
from config.settings import ES_HOST, ES_USER, ES_PASSWORD, ES_INDEX_NAME
from config.settings import SEARCH_DEFAULT_SIZE, SEARCH_MAX_SIZE
import requests
import base64

es = Elasticsearch([ES_HOST], basic_auth=(ES_USER, ES_PASSWORD), request_timeout=10)


class ImageSearcher:
    def __init__(self):
        self.index = ES_INDEX_NAME

    def build_filter_clauses(self, filters: dict) -> list:
        must_filters = []
        if not filters:
            return must_filters

        tags = filters.get("tags")
        if tags:
            must_filters.append({"terms": {"tags.keyword": tags}})

        author = filters.get("author")
        if author:
            must_filters.append({"term": {"author.keyword": author}})

        width_min = filters.get("width_min")
        width_max = filters.get("width_max")
        if width_min is not None or width_max is not None:
            range_clause = {}
            if width_min is not None:
                range_clause["gte"] = width_min
            if width_max is not None:
                range_clause["lte"] = width_max
            must_filters.append({"range": {"width": range_clause}})

        height_min = filters.get("height_min")
        height_max = filters.get("height_max")
        if height_min is not None or height_max is not None:
            range_clause = {}
            if height_min is not None:
                range_clause["gte"] = height_min
            if height_max is not None:
                range_clause["lte"] = height_max
            must_filters.append({"range": {"height": range_clause}})

        time_start = filters.get("create_time_start")
        time_end = filters.get("create_time_end")
        if time_start or time_end:
            range_clause = {}
            if time_start:
                range_clause["gte"] = time_start
            if time_end:
                range_clause["lte"] = time_end
            must_filters.append({"range": {"create_time": range_clause}})

        return must_filters

    def build_should_clauses(self, query: str, search_fields: list) -> list:
        should_clauses = []
        field_weights = self._parse_field_weights(search_fields)
        for field, boost in field_weights.items():
            should_clauses.append({
                "match": {field: {"query": query, "boost": boost}}
            })
        return should_clauses

    def _parse_field_weights(self, fields: list) -> dict:
        default_fields = {
            "title": 3.0,
            "tags": 2.0,
            "description": 1.0,
        }
        if not fields:
            return default_fields
        result = {}
        for f in fields:
            if "^" in f:
                name, weight = f.split("^", 1)
                result[name] = float(weight)
            else:
                result[f] = 1.0
        return result

    def build_sort(self, sort_type: str) -> list:
        if sort_type == "popularity":
            return [{"popularity": {"order": "desc"}}]
        elif sort_type == "time":
            return [{"create_time": {"order": "desc"}}]
        else:
            return ["_score"]

    def search(self, query: str, filters: dict = None, page: int = 1,
               size: int = SEARCH_DEFAULT_SIZE, sort: str = "relevance",
               highlight: bool = True, search_fields: list = None) -> dict:

        size = min(size, SEARCH_MAX_SIZE)
        from_offset = (page - 1) * size

        filter_clauses = self.build_filter_clauses(filters or {})
        should_clauses = self.build_should_clauses(query, search_fields)

        bool_query = {
            "must": filter_clauses,
            "should": should_clauses,
            "minimum_should_match": 1 if should_clauses else 0
        }

        body = {
            "query": {
                "bool": bool_query
            },
            "from": from_offset,
            "size": size,
            "sort": self.build_sort(sort),
            "track_total_hits": True
        }

        if highlight:
            body["highlight"] = {
                "fields": {
                    "title": {},
                    "tags": {},
                    "description": {"number_of_fragments": 1}
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }

        resp = es.search(index=self.index, body=body)
        return self._format_response(resp, page, size)

    def multimodal_search(self, query_text: str = None, query_vector: list = None,
                        mode: str = "text", hybrid_weight: float = 0.5,
                        filters: dict = None, page: int = 1,
                        size: int = SEARCH_DEFAULT_SIZE, sort: str = "relevance",
                        highlight: bool = True, search_fields: list = None) -> dict:

        size = min(size, SEARCH_MAX_SIZE)
        from_offset = (page - 1) * size

        filter_clauses = self.build_filter_clauses(filters or {})

        # 根据搜索模式构建查询
        if mode == "text":
            # 纯文本搜索
            if not query_text:
                raise ValueError("文本搜索模式需要提供query_text参数")
            return self.search(query_text, filters, page, size, sort, highlight, search_fields)

        elif mode == "image":
            # 纯图像搜索（KNN）
            if not query_vector:
                raise ValueError("图像搜索模式需要提供query_vector参数")
            return self.vector_search(query_vector, page, size, filters)

        elif mode == "hybrid":
            # 混合搜索
            if not query_text and not query_vector:
                raise ValueError("混合搜索至少需要提供query_text或query_vector参数之一")

            bool_query = {
                "must": filter_clauses
            }

            # 添加文本搜索条件
            if query_text:
                should_clauses = self.build_should_clauses(query_text, search_fields)
                for clause in should_clauses:
                    clause["match"][next(iter(clause["match"]))]["boost"] = 1.0 - hybrid_weight
                bool_query["should"] = should_clauses
                bool_query["minimum_should_match"] = 1

            # 添加向量搜索条件
            if query_vector:
                bool_query["must"].append({
                    "knn": {
                        "field": "vector",
                        "query_vector": query_vector,
                        "k": size,
                        "num_candidates": size * 10,
                        "boost": hybrid_weight * 2
                    }
                })

            body = {
                "query": {
                    "bool": bool_query
                },
                "from": from_offset,
                "size": size,
                "sort": self.build_sort(sort),
                "track_total_hits": True
            }

            if highlight and query_text:
                body["highlight"] = {
                    "fields": {
                        "title": {},
                        "tags": {},
                        "description": {"number_of_fragments": 1}
                    },
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"]
                }

            resp = es.search(index=self.index, body=body)
            result = self._format_response(resp, page, size)
            result["search_mode"] = "hybrid"
            result["hybrid_weight"] = hybrid_weight
            return result

        else:
            raise ValueError(f"不支持的搜索模式: {mode}")

    def vector_search(self, query_vector: list, k: int = 10, num_candidates: int = 100, filters: dict = None) -> dict:
        """纯向量搜索（以图搜图）"""
        filter_clauses = self.build_filter_clauses(filters or {})

        query = {
            "knn": {
                "field": "vector",
                "query_vector": query_vector,
                "k": k,
                "num_candidates": num_candidates
            }
        }

        # 如果有过滤条件，需要使用不同的查询方式
        if filter_clauses:
            query = {
                "bool": {
                    "must": filter_clauses,
                    "should": [
                        {
                            "knn": {
                                "field": "vector",
                                "query_vector": query_vector,
                                "k": k,
                                "num_candidates": num_candidates
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }

        body = {
            **query,
            "_source": ["id", "url", "title", "tags", "description", "author", "width", "height"],
            "size": k
        }

        resp = es.search(index=self.index, body=body)
        hits = [
            {
                "id": h["_id"],
                **h["_source"],
                "score": h.get("_score", 0),
            }
            for h in resp["hits"]["hits"]
        ]

        return {
            "total": len(hits),
            "page": 1,
            "size": k,
            "hits": hits,
            "search_mode": "image"
        }

    def _format_response(self, es_resp: dict, page: int, size: int) -> dict:
        hits = []
        for hit in es_resp["hits"]["hits"]:
            item = {
                "id": hit["_id"],
                **hit["_source"],
                "score": hit.get("_score", 0),
            }
            if "highlight" in hit:
                item["highlight"] = hit["highlight"]
            hits.append(item)

        return {
            "total": es_resp["hits"]["total"]["value"],
            "page": page,
            "size": size,
            "hits": hits
        }

    def suggest(self, prefix: str, field: str = "tags.keyword", size: int = 10) -> list:
        body = {
            "suggest": {
                "tag_suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": field,
                        "size": size
                    }
                }
            }
        }
        try:
            resp = es.search(index=self.index, body=body)
            options = resp["suggest"]["tag_suggest"][0].get("options", [])
            return [opt["text"] for opt in options]
        except Exception:
            return []

    @staticmethod
    def extract_image_features(image_data: bytes) -> list:
        """提取图片特征向量（模拟实现，实际需要使用CLIP等模型）"""
        # 注意：这里是一个简化的示例实现
        # 实际项目中应该集成CLIP、ViT等视觉模型来提取真实的图片特征
        import numpy as np
        import hashlib

        # 使用图片数据的哈希来生成"伪"特征向量
        # 在实际应用中，这里应该调用真实的特征提取模型
        hash_obj = hashlib.sha256(image_data)
        hash_bytes = hash_obj.digest()

        # 将哈希转换为768维的浮点向量（CLIP标准维度）
        np_hash = np.frombuffer(hash_bytes, dtype=np.uint8)
        vector = np.zeros(768, dtype=np.float32)

        # 简单的填充策略
        for i, val in enumerate(np_hash):
            vector[i % 768] = val / 255.0

        return vector.tolist()

    @staticmethod
    def download_image(url: str) -> bytes:
        """下载图片并返回字节数据"""
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content

    @staticmethod
    def decode_base64_image(base64_string: str) -> bytes:
        """解码Base64图片数据"""
        # 移除可能的数据URI前缀
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        return base64.b64decode(base64_string)


if __name__ == "__main__":
    searcher = ImageSearcher()
    result = searcher.search(
        query="红色跑车",
        filters={"tags": ["汽车"], "width_min": 1920},
        page=1,
        size=5
    )
    print(f"共找到 {result['total']} 条结果:")
    for h in result["hits"]:
        print(f"  [{h['score']:.2f}] {h['title']}")
