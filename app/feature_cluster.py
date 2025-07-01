import redis
import json
import time
import base64
import torch
import numpy as np
from types import SimpleNamespace
from PIL import Image
from loguru import logger
from utils import multi_pop
from config import Config
from model import VIT_MSN

db = redis.StrictRedis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB
)
logger.info(f"Connected to Redis server {Config.REDIS_HOST}:{Config.REDIS_PORT}")

class FeatureExtraction():
    def __init__(self):
        DEVICE = Config.DEVICE
        self.extractor = VIT_MSN(device=DEVICE)
        self.extractor.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def run(self):
        while True:
            t0 = time.time()
            # Get batch requests
            raw_requests = multi_pop(
                db, Config.REDIS_QUEUE, Config.MAX_BATCH_SIZE_EMBEDDING)
            end_get = time.time()
            verified_request = []
            # step 1: parsing requests
            for req in raw_requests:
                if req is None:
                    continue
                req_payload = json.loads(
                    req,
                    object_hook= lambda x: SimpleNamespace(**x)  # convert to object
                )
                verified_request.append(req_payload)

            if len(verified_request) == 0:
                time.sleep(Config.SERVER_SLEEP)
                continue
            logger.info("Time get request: {}".format(end_get - t0))
            logger.info("Loaded success")

            # Decode images from base64
            images = []
            image_ids = []
            for payload in verified_request:
                rq_id = payload.id
                img_str = db.get(Config.IMAGE_PREFIX + rq_id)
                db.delete(Config.IMAGE_PREFIX + rq_id)
                img_shape = (payload.height, payload.width, 3)
                img_arr = np.frombuffer(
                    base64.b64decode(img_str),
                    dtype=np.uint8
                )
                img_arr = img_arr.reshape(img_shape)
                images.append(Image.fromarray(img_arr).convert("RGB"))
                image_ids.append(rq_id)

            start_extract = time.time()
            features = self.extractor.get_features(images)
            end_extract = time.time()

            for (img_id, feat) in zip(image_ids, features):
                db.set(img_id, base64.b64encode(feat.astype(np.float32)).decode("utf-8"))

            logger.info("Time extract feature: {}".format(end_extract - start_extract))
            logger.info("Time Extract: {}".format(time.time() - t0))
            
            verified_request.clear()

            time.sleep(Config.SERVER_SLEEP)

if __name__ == "__main__":
    runner = FeatureExtraction()
    runner.run()