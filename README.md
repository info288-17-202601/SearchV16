# SearchV16
SearchV16 es un motor de búsqueda distribuido de alto rendimiento diseñado para entornos corporativos. El sistema permite la indexación y recuperación eficiente de grandes volúmenes de documentos mediante una arquitectura de cuatro capas, garantizando seguridad a nivel de documento y alta disponibilidad.


# Ejecución ElasticSearch

ElasticSearch (la primera vez)
```
docker run --name elasticsearch \
-p 9200:9200 \
-p 9300:9300 \
-e "discovery.type=single-node" \
-e "xpack.security.enabled=false" \
docker.elastic.co/elasticsearch/elasticsearch:8.13.4
```

Luego:

```
docker start elasticsearch
```

```
docker stop elasticsearch
```

Kibana
```
docker run -p 5601:5601 --link elasticsearch:elasticsearch docker.elastic.co/kibana/kibana:8.13.4
```