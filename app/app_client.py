import argparse
import io
import gradio as gr
import requests
import ast
from config import Config

TITLE = "# Image Retrieval" 
DESCRIPTION = """
# Push an image or Find similar images
"""

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--share", action="store_true")
    return parser.parse_args()

class SimilaritySearcher:
    def __init__(self, server_host, image_folder):
        self.search_endpoint = server_host + '/search_image/'
        self.push_endpoint = server_host + '/push_image/'
        self.image_dir = image_folder

    def search(self, image):
        image_ids = []
        results = []
        try:
            image = self.gr_image_to_bytes(image)
            response = requests.post(
                self.search_endpoint,
                files={Config.FILE_KEY: ('custom_filename.jpg', image, 'image/jpeg')},
            )
        
            if response.status_code == 200:
                results =  ast.literal_eval(response.content.decode('utf-8'))
                image_ids = [item for item in results]
                return self.get_image_by_ids(image_ids)
            else:
                print(f"Search request failed with status code: {response.status_code}")
                return None
        except requests.Timeout:
            print("Request timed out after", Config.REQUEST_TIMEOUT, "seconds")
            return None
        except requests.RequestException as e:
            print("Request failed:", e)
            return None
                
    def push(self, image):
        results = []
        try:
            image = self.gr_image_to_bytes(image)
            response = requests.post(
                self.push_endpoint,
                files={Config.FILE_KEY: image},
            )
        
            if response.status_code == 200:
                results =  response.json()
                signed_url = results['signed_url']
                return self.get_image_by_ids([signed_url])
            else:
                print("Request failed with status code:", response.status_code)
                return None
        except requests.Timeout:
            print("Request timed out after", Config.REQUEST_TIMEOUT, "seconds")
            return None
        except requests.RequestException as e:
            print("Request failed:", e)
            return None
    
    def get_image_by_ids(self, image_ids):
        image_urls = []
        caps = []
        for image_id in image_ids:
            cap = f'{image_id}'
            image_urls.append(image_id)
            caps.append(cap)
        return list(zip(image_urls, caps))

    @staticmethod
    def gr_image_to_bytes(image):
        image_pil = image
        image_buffer = io.BytesIO()
        image_pil.save(image_buffer, format='JPEG')
        image_buffer.seek(0)
        return image_buffer.getvalue()

def run():
    args = parse_args()
    searcher = SimilaritySearcher(server_host=Config.SERVER_HOST, image_folder=Config.DB_IMAGE_FOLDER)
    print(searcher.search_endpoint)

    with gr.Blocks() as demo:
        gr.Markdown(TITLE)
        gr.Markdown(DESCRIPTION)

        with gr.Row():
            input = gr.Image(type="pil", label="Input")

            with gr.Column():
                find_btn = gr.Button("Find similar images")
                push_btn = gr.Button("Push image")

        results = gr.Gallery(label="Results", columns=5)

        find_btn.click(
            fn=searcher.search,
            inputs=[
                input,
            ],
            outputs=[results],
        )

        push_btn.click(
            fn=searcher.push,
            inputs=[
                input
            ],
            outputs=[results],
        )
    # demo.queue()
    demo.launch(share=args.share)



if __name__ == "__main__":
    run()