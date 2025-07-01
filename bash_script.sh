#!/bin/bash

cd app || { echo "Cannot change to app directory"; exit 1; }
read -p "Do you want to share the application? (y/n): " share_input
python feature_cluster.py &
uvicorn main:app --host 0.0.0.0 --port 8005 &
if [[ "$share_input" == "y" || "$share_input" == "Y" ]]; then
    python app_client.py --share
else
    python app_client.py
fi
wait