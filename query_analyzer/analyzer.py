from elasticsearch import Elasticsearch
from config.settings import ES_HOST, ES_USER, ES_PASSWORD, ES_INDEX_NAME

es = Elasticsearch([ES_HOST], basic_auth=(ES_USER, ES_PASSWORD), request_timeout=10)

DEFAULT_SYNONYMS = {
    "汽车": ["轿车", "机动车", "车辆"],
    "跑车": ["赛车", "轿跑"],
    "风景": ["景色", "景观", "风光"],
    "猫": ["猫咪", "小猫", "cat"],
    "狗": ["狗狗", "小狗", "dog"],
}


class QueryAnalyzer:
    def __init__(self):
        self.synonym_cache = {}

    def spell_correct(self, query: str) -> str:
        try:
            body = {
                "text": query,
                "term": {
                    "field": "title",
                    "string_distances": ["levenshtein"],
                    "max_edits": 2,
                    "prefix_length": 3,
                    "size": 1
                }
            }
            resp = es.suggest(body=body, index=ES_INDEX_NAME)
            suggestions = resp.get("term", [])
            if suggestions and suggestions[0].get("options"):
                return suggestions[0]["options"][0]["text"]
        except Exception:
            pass
        return query

    def get_synonyms(self, word: str) -> str:
        if word in self.synonym_cache:
            return self.synonym_cache[word]
        from data_sync.sync import get_synonyms
        synonyms = get_synonyms(word)
        if not synonyms:
            synonyms = DEFAULT_SYNONYMS.get(word, [])
        result = " ".join(synonyms)
        self.synonym_cache[word] = result
        return result

    def to_pinyin(self, text: str) -> str:
        try:
            from pypinyin import lazy_pinyin
            parts = []
            for ch in text:
                if '\u4e00' <= ch <= '\u9fff':
                    pys = lazy_pinyin(ch)
                    parts.append("".join(pys))
                else:
                    parts.append(ch.lower())
            return "".join(parts)
        except ImportError:
            return ""

    def analyze(self, raw_query: str) -> dict:
        corrected = self.spell_correct(raw_query)
        synonym_parts = []
        for token in corrected.split():
            syn = self.get_synonyms(token)
            if syn:
                synonym_parts.append(syn)
        expanded_synonyms = " ".join(synonym_parts)
        pinyin = self.to_pinyin(corrected)
        expanded_query = corrected
        if expanded_synonyms:
            expanded_query += " " + expanded_synonyms

        return {
            "original": raw_query,
            "corrected": corrected,
            "expanded": expanded_query,
            "pinyin": pinyin,
            "has_correction": corrected != raw_query
        }


if __name__ == "__main__":
    analyzer = QueryAnalyzer()
    result = analyzer.analyze("红色跑车")
    print("查询分析结果:", result)
