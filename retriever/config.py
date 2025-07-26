import os
class Config:
    # Config for Pinecone
    INDEX_NAME = "mlops1-project"
    INPUT_RESOLUTION = 768
    PINECONE_CLOUD = "gcp"
    PINECONE_REGION = "us-central1"
    # Config for retriever
    TOP_K = 5
    # Config for GCS    
    GCS_BUCKET_NAME = "mlops1-project-bucket"
    # Config for embedding service
    EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://vit-msn-service:5000/embed")