# Run
uvicorn main:app --host 0.0.0.0 --port 5002

# Build docker image and Run docker container
docker compose -f retriever-docker-compose.yaml up -d 

# Remove and rebuild
docker compose -f retriever-docker-compose.yaml down --remove-orphans
docker compose -f retriever-docker-compose.yaml up --build