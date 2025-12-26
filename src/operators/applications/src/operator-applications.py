import kopf
import logging

@kopf.on.create('applications')
def on_create(body, **kwargs):
    logging.info(f"Create Resource: {body['metadata']['name']}")
