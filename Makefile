.PHONY: all 
APP_DIR = app
UVICORN_CMD = uvicorn main:app --host 0.0.0.0 --port 8005
FEATURE_CLUSTER_CMD = python feature_cluster.py
APP_CLIENT_CMD = python app_client.py
SHARE_FLAG = --share

all:
	cd $(APP_DIR) && $(FEATURE_CLUSTER_CMD) & \
	cd $(APP_DIR) && $(UVICORN_CMD) & \
	cd $(APP_DIR) && bash -c 'read -p "Do you want to share the application? (y/n): " share_input; \
	if [[ "$$share_input" == "y" || "$$share_input" == "Y" ]]; then \
		$(APP_CLIENT_CMD) $(SHARE_FLAG); \
	else \
		$(APP_CLIENT_CMD); \
	fi'