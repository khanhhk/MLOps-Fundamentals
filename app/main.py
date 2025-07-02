import threading
import uuid, time, datetime, base64, json
import numpy as np

import redis
from PIL import Image
from loguru import logger
from fastapi import FastAPI, UploadFile, File, HTTPException
import gradio as gr
from io import BytesIO

from config import Config
from utils import get_index, search, get_storage_client
from app_client import create_demo
from feature_cluster import FeatureExtraction

db = redis.StrictRedis(
    host=Config.REDIS_HOST, 
    port=Config.REDIS_PORT, 
    db=Config.REDIS_DB)
logger.info(f"Connected to Redis {Config.REDIS_HOST}:{Config.REDIS_PORT}")

index = get_index(Config.INDEX_NAME)
logger.info(f"Pinecone index: {Config.INDEX_NAME}")

# GCS client
try:
    storage_client = get_storage_client()
    bucket = storage_client.get_bucket(Config.GCS_BUCKET_NAME)
    if not bucket.exists():
        logger.error(f"Bucket {Config.GCS_BUCKET_NAME} not found in Google Cloud Storage.")
        raise HTTPException(status_code=404, detail=f"Bucket {Config.GCS_BUCKET_NAME} not found.")

    logger.info(f"Connected to GCS bucket '{Config.GCS_BUCKET_NAME}' successfully")
except Exception as e:
    logger.error(f"Error accessing GCS bucket '{Config.GCS_BUCKET_NAME}': {e}")
    raise HTTPException(status_code=500, detail=str(e))


# --- FastAPI app ---
app = FastAPI()

@app.on_event("startup")
def start_background():
    t = threading.Thread(target=FeatureExtraction().run, daemon=True)
    t.start()
    logger.info("FeatureExtraction thread started")

@app.get("/health_check/")
def health_check():
    return {"status": "OK!"}

@app.post("/push_image/")
async def push_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # generate a unique id for the image
        unique_id = str(uuid.uuid4())
        image_str = base64.b64encode(np.asarray(image)).decode("utf-8")
        extract_object = {
            "id": unique_id,
            "width": image.width,
            "height": image.height
        }
        start_time = time.time()
        db.set(Config.IMAGE_PREFIX + unique_id, image_str)
        db.rpush(Config.REDIS_QUEUE, json.dumps(extract_object))
        end_time = time.time()
        logger.info(f"Pushed image to Redis queue in {end_time - start_time:.4f} seconds")
        
        t0 = time.time()
        while True:
            rq_time = time.time() - t0
            if rq_time > Config.REQUEST_TIMEOUT:
                break
            out = db.get(unique_id)
            if not out:
                continue
            db.delete(unique_id)

            feature = np.frombuffer(base64.b64decode(out), dtype=np.float32)
            feature = feature.reshape(1, -1).flatten().tolist()

        file_extension = "JPEG" if file.filename.split(".")[-1].upper() in ["JPG", "FILE"] else file.filename.split(".")[-1].upper()  
        gcs_file_path = f"images/{unique_id}.{file_extension}"

        # upload the file to GCS
        blob = bucket.blob(gcs_file_path)
        if not blob.exists():
            try:
                blob.upload_from_string(image_bytes, content_type=file.content_type)
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(hours=1),
                    method="GET")
                logger.info(f"Uploaded image to GCS successfully: {gcs_file_path}")
            except Exception as e:
                logger.error(f"Failed to upload image to GCS: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to upload image to GCS: {e}")
        else:
            logger.warning(f"Image already exists: {gcs_file_path}")

        index.upsert([(
            unique_id,
            feature,
            {"gcs_path": gcs_file_path, "file_name": file.filename}
        )])
        logger.info(f"Upserted image to index successfully: {unique_id}")
        return {"message": "Successfully!", "file_id": unique_id, "gcs_file_path": gcs_file_path, "signed_url": signed_url}
    except Exception as e:
        logger.error(f"Error in pushing image: {e}")
        raise HTTPException(status_code=500, detail=f"Error in pushing image: {e}")
    
@app.post("/search_image/")
async def search_image(file: UploadFile = File(...)):
    try:
        logger.info('Started image search process')
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        logger.info('Image successfully loaded and converted to RGB')

        image_id = str(uuid.uuid4())
        image_str = base64.b64encode(np.asarray(image)).decode("utf-8")
        extract_object = {
            "id": image_id,
            "width": image.width,
            "height": image.height
        }
        start_time = time.time()
        db.set(Config.IMAGE_PREFIX + image_id, image_str)
        db.rpush(Config.REDIS_QUEUE, json.dumps(extract_object))
        end_time = time.time()
        logger.info(f"Pushed image to Redis queue in {end_time - start_time:.4f} seconds")
        match_ids = []
        t0 = time.time()

        while True:
            rq_time = time.time() - t0
            if rq_time > Config.REQUEST_TIMEOUT:
                break
            out = db.get(image_id)
            if not out:
                continue
            db.delete(image_id)

            feature = np.frombuffer(base64.b64decode(out), dtype=np.float32)
            feature = feature.reshape(1, -1).flatten().tolist()

            start_time = time.time()
            match_ids = search(index, feature, top_k=Config.TOP_K * 4)
            elapsed_time = time.time() - start_time
            logger.info(f'Search completed in {elapsed_time:.4f} seconds')
            response = index.fetch(ids=match_ids)
            break

        images_url = []
        for match_id in match_ids:
            if len(images_url) == Config.TOP_K:
                break
            if match_id in response.get('vectors', {}):
                metadata = response['vectors'][match_id].get("metadata", {})
                gcs_path = metadata.get("gcs_path", "")
                blob = bucket.blob(gcs_path)
                if not blob.exists():
                    logger.warning(f"Image with GCS path {gcs_path} does not exist in bucket.")
                    continue
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(hours=1),
                    method="GET")
                images_url.append(signed_url)
                logger.info(f"Found URL for match ID {match_id}")
            else:
                logger.warning(f"Match ID {match_id} not found in response.")
        return images_url
    except Exception as e:
        logger.error(f"Error in image search process: {e}")
        raise HTTPException(status_code=400, detail=f"Error in image search process: {e}")

# args = parse_args()
# demo = create_demo().launch(share=args.share)
# app.mount("/", WSGIMiddleware(demo))

demo = create_demo()

app = gr.mount_gradio_app(app, demo, path="/")

# --- chạy server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT_EXPOSE)
