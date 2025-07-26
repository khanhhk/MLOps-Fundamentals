import os
import time
import redis
from pinecone import Pinecone, ServerlessSpec
from loguru import logger
from google.cloud import storage
from google.oauth2 import service_account
from config import Config
from model import VIT_MSN
import torch
import json
from types import SimpleNamespace
import base64
import numpy as np
from PIL import Image

PINECONE_APIKEY = os.environ["PINECONE_APIKEY"]

def get_index(index_name):
    pc = Pinecone(api_key=PINECONE_APIKEY)
    # if index_name in pc.list_indexes().names():
    #     pc.delete_index(index_name)
    #     logger.info(f"Deleted existing Pinecone index: {index_name}")
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            metric="cosine",
            dimension=Config.INPUT_RESOLUTION,
            spec=ServerlessSpec(
                cloud = Config.PINECONE_CLOUD,
                region = Config.PINECONE_REGION
            )
        )
        logger.info(f"Created Pinecone index: {index_name}")
    return pc.Index(index_name)

def get_storage_client():
    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if json_path:
        credentials = service_account.Credentials.from_service_account_file(json_path)
        return storage.Client(credentials=credentials)
    return storage.Client()

def search(index, input_emb, top_k):
    if not input_emb:
        raise ValueError("Input embedding is empty")
    matching = index.query(vector=input_emb, top_k=top_k, include_values=True)[
        "matches"
    ]
    match_ids = [match_id["id"] for match_id in matching]
    return match_ids

