"""Harmless scaffold worker: no model/network calls."""
import json
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def handler(event, context):
    for record in event.get("Records", []):
        task = json.loads(record["body"])
        log.info("Received task_id=%s", task.get("task_id", "unknown"))
    return {"received": len(event.get("Records", []))}
