import torch
class Config:
    PORT_EXPOSE = 30000

    # Config for Pinecone
    INDEX_NAME = "mlops1-project"
    INPUT_RESOLUTION = 384
    PINECONE_CLOUD = "gcp"
    PINECONE_REGION = "us-central1"

    # Config for model
    MODEL_PATH = "./models"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


    TOP_K = 5
    MAX_BATCH_SIZE_EMBEDDING = 32
    SERVER_SLEEP = 0.05
    
    # Config for GCS    
    GCS_BUCKET_NAME = "mlops1-project-bucket"

    # Config redis db
    REDIS_HOST = "127.0.0.1"
    REDIS_DB = 0
    REDIS_PORT = 6379
    REDIS_QUEUE = "extract_feature_queue"
    REQUEST_TIMEOUT = 10
    IMAGE_PREFIX = "image_"
    SERVER_HOST = f"http://{REDIS_HOST}:{PORT_EXPOSE}"

    # Config for gradio
    FILE_KEY = "file"
    DB_IMAGE_FOLDER = 'data/oxbuild/images'