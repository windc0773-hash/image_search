from elasticsearch import Elasticsearch
from config.settings import ES_HOST, ES_USER, ES_PASSWORD, ES_INDEX_NAME, ES_SYNONYM_INDEX

def get_es_client():
    return Elasticsearch(
        [ES_HOST],
        basic_auth=(ES_USER, ES_PASSWORD),
        request_timeout=30,
        max_retries=3,
    )

IMAGE_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 5,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "ik_smart_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_smart"
                },
                "ik_max_word_analyzer": {
                    "type": "custom",
                    "tokenizer": "ik_max_word"
                },
                "pinyin_analyzer": {
                    "tokenizer": "pinyin_tokenizer",
                    "filter": ["lowercase"]
                }
            },
            "tokenizer": {
                "pinyin_tokenizer": {
                    "type": "pinyin",
                    "keep_first_letter": True,
                    "keep_separate_first_letter": False,
                    "keep_full_pinyin": True,
                    "keep_original": True,
                    "limit_first_letter_length": 16,
                    "lowercase": True
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "url": {"type": "keyword", "index": False},
            "title": {
                "type": "text",
                "analyzer": "ik_max_word_analyzer",
                "search_analyzer": "ik_smart_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "pinyin": {"type": "text", "analyzer": "pinyin_analyzer"}
                }
            },
            "tags": {
                "type": "text",
                "analyzer": "ik_max_word_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "description": {
                "type": "text",
                "analyzer": "ik_max_word_analyzer"
            },
            "author": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "create_time": {"type": "date"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "size_bytes": {"type": "long"},
            "popularity": {"type": "float"},
            "vector": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "cosine"
            }
        }
    }
}

SYNONYM_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "word": {"type": "keyword"},
            "synonyms": {"type": "text", "analyzer": "whitespace"}
        }
    }
}


class IndexManager:
    def __init__(self):
        self.es = get_es_client()
        self.index_name = ES_INDEX_NAME
        self.synonym_index = ES_SYNONYM_INDEX

    def init_image_index(self):
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=IMAGE_INDEX_MAPPING)
            print(f"索引 {self.index_name} 创建成功")
        else:
            print(f"索引 {self.index_name} 已存在")

    def init_synonym_index(self):
        if not self.es.indices.exists(index=self.synonym_index):
            self.es.indices.create(index=self.synonym_index, body=SYNONYM_INDEX_MAPPING)
            print(f"同义词索引 {self.synonym_index} 创建成功")
        else:
            print(f"同义词索引 {self.synonym_index} 已存在")

    def delete_index(self, name=None):
        target = name or self.index_name
        if self.es.indices.exists(index=target):
            self.es.indices.delete(index=target)
            print(f"索引 {target} 已删除")

    def health_check(self):
        return self.es.cluster.health()

    def refresh(self, name=None):
        target = name or self.index_name
        self.es.indices.refresh(index=target)

    def count_documents(self):
        """统计索引中的文档数量"""
        try:
            result = self.es.count(index=self.index_name)
            return result.get("count", 0)
        except Exception:
            return 0

    def get_all_tags(self, size=1000):
        """获取所有标签及其出现次数"""
        try:
            body = {
                "size": 0,
                "aggs": {
                    "tags": {
                        "terms": {
                            "field": "tags.keyword",
                            "size": size
                        }
                    }
                }
            }
            result = self.es.search(index=self.index_name, body=body)
            buckets = result.get("aggregations", {}).get("tags", {}).get("buckets", [])
            tags = [{"tag": b["key"], "count": b["doc_count"]} for b in buckets]
            return {"tags": tags, "total": len(tags)}
        except Exception as e:
            print(f"获取标签失败: {e}")
            return {"tags": [], "total": 0}

    def get_average_score(self):
        """计算平均评分（使用popularity作为评分）"""
        try:
            body = {
                "size": 0,
                "aggs": {
                    "avg_score": {
                        "avg": {
                            "field": "popularity",
                            "missing": 0
                        }
                    }
                }
            }
            result = self.es.search(index=self.index_name, body=body)
            avg_score = result.get("aggregations", {}).get("avg_score", {}).get("value", 0)
            return {"avg_score": avg_score if avg_score else 0}
        except Exception as e:
            print(f"计算平均评分失败: {e}")
            return {"avg_score": 0}

    def get_recent_images(self, size=10):
        """获取最近添加的图片"""
        try:
            body = {
                "size": size,
                "sort": [{"create_time": {"order": "desc"}}],
                "_source": ["id", "url", "title", "tags", "create_time"]
            }
            result = self.es.search(index=self.index_name, body=body)
            hits = result.get("hits", {}).get("hits", [])
            images = [{"id": h["_id"], **h["_source"]} for h in hits]
            return {"images": images, "total": len(images)}
        except Exception as e:
            print(f"获取最近图片失败: {e}")
            return {"images": [], "total": 0}

    def get_popular_images(self, size=10):
        """获取热门图片"""
        try:
            body = {
                "size": size,
                "sort": [{"popularity": {"order": "desc"}}],
                "_source": ["id", "url", "title", "tags", "popularity"]
            }
            result = self.es.search(index=self.index_name, body=body)
            hits = result.get("hits", {}).get("hits", [])
            images = [{"id": h["_id"], **h["_source"]} for h in hits]
            return {"images": images, "total": len(images)}
        except Exception as e:
            print(f"获取热门图片失败: {e}")
            return {"images": [], "total": 0}


if __name__ == "__main__":
    mgr = IndexManager()
    mgr.init_image_index()
    mgr.init_synonym_index()
    print("集群健康:", mgr.health_check()["status"])
    print("文档数量:", mgr.count_documents())
