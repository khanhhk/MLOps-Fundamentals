import uuid
import time
import datetime
import requests
from PIL import Image
from io import BytesIO
from fastapi import FastAPI, UploadFile, File, HTTPException
from loguru import logger
from config import Config
from utils import get_index, search, get_storage_client


index = get_index(Config.INDEX_NAME)
logger.info(f"Pinecone index: {Config.INDEX_NAME}")

GCS_BUCKET_NAME = Config.GCS_BUCKET_NAME
try:
    storage_client = get_storage_client()
    bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
    if not bucket.exists():
        logger.error(f"Bucket {GCS_BUCKET_NAME} not found in Google Cloud Storage.")
        raise HTTPException(status_code=404, detail=f"Bucket {GCS_BUCKET_NAME} not found.")

    logger.info(f"Connected to GCS bucket '{GCS_BUCKET_NAME}' successfully")
except Exception as e:
    logger.error(f"Error accessing GCS bucket '{GCS_BUCKET_NAME}': {e}")
    raise HTTPException(status_code=500, detail=str(e))

def get_feature_vector(image: Image.Image) -> list:
    try:
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()
        response = requests.post(
            url=Config.EMBEDDING_SERVICE_URL,
            files={"file": ("image.jpg", img_bytes, "image/jpeg")}
        )
        response.raise_for_status()
        feature = response.json()["embedding"]
        return feature
    except Exception as e:
        logger.error(f"Failed to get feature vector: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feature vector from embedding service")
    
app = FastAPI()

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

        feature = get_feature_vector(image)

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

        feature = get_feature_vector(image)

        start_time = time.time()
        match_ids = search(index, feature, top_k=Config.TOP_K * 4)
        elapsed_time = time.time() - start_time
        logger.info(f'Search completed in {elapsed_time:.4f} seconds')
        response = index.fetch(ids=match_ids)

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