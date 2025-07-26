# Run
uvicorn main:app --host 0.0.0.0 --port 5001

# Build docker image and Run docker container
docker compose -f ingesting-docker-compose.yaml up -d 
