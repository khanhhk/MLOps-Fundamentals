import os
class Config:
    # Config for Pinecone
    INDEX_NAME = "mlops1-project"
    INPUT_RESOLUTION = 768
    PINECONE_CLOUD = "gcp"
    PINECONE_REGION = "us-central1"  
    # Config for GCS    
    GCS_BUCKET_NAME = "mlops1-project-bucket"
    PUBSUB_TOPIC = "projects/mlek3-19072003/topics/mlops1-project-topic"
    # Config for embedding service
    EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://vit-msn-service:5000/embed")