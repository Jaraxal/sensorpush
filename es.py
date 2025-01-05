import logging
from collections.abc import Generator
from typing import Any

from elasticsearch import Elasticsearch, helpers

logger = logging.getLogger()


def send_to_elasticsearch(es_client: Elasticsearch, records: list[dict[str, Any]], index_name: str) -> None:
    logger.info(f"Sending [{len(records)}] records to Elasticsearch index [{index_name}].")
    try:
        success = 0
        for ok, action in helpers.streaming_bulk(client=es_client, actions=document_generator(records, index_name)):
            if not ok:
                logger.error(f"Failed to index document: {action}")
            else:
                success += 1
        logger.info(f"Successfully indexed [{success}] records.")
    except Exception as e:
        logger.error(f"Elasticsearch indexing error: {e}")


def document_generator(records: list[dict[str, Any]], index_name: str) -> Generator[dict[str, Any], None, None]:
    for record in records:
        yield {
            "_op_type": "create",
            "_index": index_name,
            "_id": record["hash"],
            "_source": record,
        }
