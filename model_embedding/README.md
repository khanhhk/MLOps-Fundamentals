# Run
uvicorn main:app --host 0.0.0.0 --port 5000

# Build docker image
docker build -t vit-msn-service .

# Run docker container
docker run --name vit-msn-container -p 5000:5000 vit-msn-service