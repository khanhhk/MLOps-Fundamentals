python=3.9.19
# run feature_cluster.py
python feature_cluster.py
# run main.py
uvicorn main:app --host 0.0.0.0 --port 8005
# run gradio_client.py
python app_client.py