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