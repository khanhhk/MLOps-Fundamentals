import os
import time
import redis
from pinecone import Pinecone, ServerlessSpec
from loguru import logger
from config import Config

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

def search(index, input_emb, top_k):
    if not input_emb:
        raise ValueError("Input embedding is empty")
    matching = index.query(vector=input_emb, top_k=top_k, include_values=True)[
        "matches"
    ]
    match_ids = [match_id["id"] for match_id in matching]
    return match_ids

def multi_pop(r, q, n):
    arr = []
    count = 0
    while True:
        try:
            p = r.pipeline()
            p.multi()
            for i in range(n):
                p.lpop(q)
            arr = p.execute()
            return arr
        except redis.ConnectionError as e:
            print(e)
            count += 1
            logger.error("Connection failed in %s times" % count)
            if count > 3:
                raise
            backoff = count * 5
            logger.info('Retrying in {} seconds'.format(backoff))
            time.sleep(backoff)
            r = redis.StrictRedis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB
            )