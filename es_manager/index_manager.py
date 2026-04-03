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


if __name__ == "__main__":
    mgr = IndexManager()
    mgr.init_image_index()
    mgr.init_synonym_index()
    print("集群健康:", mgr.health_check()["status"])
