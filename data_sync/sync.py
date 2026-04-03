from elasticsearch.helpers import bulk
from es_manager.index_manager import get_es_client
from config.settings import ES_INDEX_NAME

es = get_es_client()


def upsert_image(doc: dict):
    body = {
        "doc": doc,
        "doc_as_upsert": True
    }
    return es.update(index=ES_INDEX_NAME, id=doc["id"], body=body)


def batch_upsert_images(docs: list, batch_size=500):
    actions = []
    for doc in docs:
        action = {
            "_op_type": "update",
            "_index": ES_INDEX_NAME,
            "_id": doc["id"],
            "doc": doc,
            "doc_as_upsert": True
        }
        actions.append(action)
        if len(actions) >= batch_size:
            bulk(es, actions, raise_on_error=False)
            actions = []
    if actions:
        bulk(es, actions, raise_on_error=False)


def delete_image(image_id: str):
    return es.delete(index=ES_INDEX_NAME, id=image_id, ignore=[404])


def get_image(image_id: str):
    return es.get(index=ES_INDEX_NAME, id=image_id, ignore=[404])


def add_synonym(word: str, synonyms: list):
    from config.settings import ES_SYNONYM_INDEX
    body = {"word": word, "synonyms": " ".join(synonyms)}
    return es.update(
        index=ES_SYNONYM_INDEX, id=word,
        body={"doc": body, "doc_as_upsert": True}
    )


def get_synonyms(word: str) -> list:
    from config.settings import ES_SYNONYM_INDEX
    resp = es.get(index=ES_SYNONYM_INDEX, id=word, ignore=[404])
    if resp.get("found"):
        return resp["_source"].get("synonyms", "").split()
    return []


if __name__ == "__main__":
    sample_doc = {
        "id": "img_001",
        "url": "https://example.com/img_001.jpg",
        "title": "红色法拉利跑车",
        "tags": ["汽车", "红色", "跑车"],
        "description": "一辆红色的法拉利跑车停在赛道上",
        "author": "张三",
        "create_time": "2024-01-15T10:00:00",
        "width": 3840,
        "height": 2160,
        "size_bytes": 2048576,
        "popularity": 9.5
    }
    result = upsert_image(sample_doc)
    print("写入结果:", result["result"])
