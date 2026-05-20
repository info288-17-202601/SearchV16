from elasticsearch import Elasticsearch
import sys


es = Elasticsearch("http://localhost:9200")

# AND
def busquedaSimple(query):
    response = es.search(
        index="library",
        query={
            "match": {
                "content": {
                    "query": query,
                }
            }
        }
    )

    # Leer los resultados
    for hit in response["hits"]["hits"]:
        print(hit["_score"])
        print(hit["_source"]["title"])
# Filtro fecha
# response = es.search(
#     index="library",
#     query={
#         "range": {
#             "year": {
#                 "gte": 2020,
#                 "lte": 2025
#             }
#         }
#     }
# )

# Frase exacta
# response = es.search(
#     index="library",
#     query={
#         "match_phrase": {
#             "content": "distributed systems"
#         }
#     }
# )

# Filtro autor
# response = es.search(
#     index="library",
#     query={
#         "bool": {
#             "must": [
#                 {"match": {"content": "consensus"}}
#             ],

#             "filter": [
#                 {"term": {"author.keyword": "Tanenbaum"}}
#             ]
#         }
#     }
# )

# MUST y busqueda en varios campos
# response = es.search(
#     index="library",
#     query={
#         "must": [
#             {
#                 "multi_match": {
#                     "query": "distributed systems",
#                     "fields": ["title", "content"]
#                 }
#             }
#         ],
#     }
# )



# Highlight
# response = es.search(
#     index="library",
#     query={
#         "match": {
#             "content": "consensus"
#         }
#     },

#     highlight={
#         "fields": {
#             "content": {}
#         }
#     }
# )

# for hit in response["hits"]["hits"]:

#     print(hit["_source"]["title"])

#     if "highlight" in hit:
#         print(hit["highlight"]["content"])

if __name__ == "__main__":
    if not len(sys.argv) == 2:
        raise ValueError("Debe llamar como python busqueda.py N, donde N es la query")
    query = sys.argv[1]
    busquedaSimple(query=query)