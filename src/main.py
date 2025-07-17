import json
import os
from flask import Flask, Response
from flask_cors import CORS
from flask import request
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from ollama import Client

load_dotenv()
PORT = os.getenv(key='PORT', default=5500)
OLLAMA_HOST = os.getenv(key='OLLAMA_HOST', default="")
EMBEDDING_MODEL = os.getenv(key='EMBEDDING_MODEL', default="")
QDRANT_HOST = os.getenv(key='QDRANT_HOST', default="")
QDRANT_PORT = os.getenv(key='QDRANT_PORT', default="")

# Flask App setup ____________________________________________________
app = Flask(__name__)
cors = CORS(app, origins="*")

# AI stuff ___________________________________________________________
qdrant = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
ollama = Client(host=OLLAMA_HOST)


def query_obsidian(prompt: str):
    print(prompt)
    embeddings = ollama.embed(model=EMBEDDING_MODEL, input=prompt)
    embedding = embeddings.embeddings[0]
    hits = qdrant.query_points(
        collection_name="PluginDev",
        query=embedding,
        # score_threshold=.6,
        limit=10,
        # query_filter={}
    )

    results = ""
    for item in hits.points:
        results = f'{results}\n{item.payload.get("content")}\n{"-" * 20}\n'

    response = f"Here is related contexts from user's notes\n<notes>{results}</notes>"
    return response


def messages_to_prompt(messages):
    prompts = ""
    if messages:
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if role == "user":
                prompts = f"{prompts}\nUser: {content}"
            elif role == "assistant":
                prompts = f"{prompts}\nAssistant: {content}"

    return prompts


@app.route('/inlet', methods=["POST"])
def inlet():
    data = request.get_json()
    body = data.get("body")
    metadata = body.get("metadata")
    user_id = metadata.get("user_id")
    task = metadata.get("task")
    messages = body.get("messages")
    print(f"task: {task}")
    print(f"uid: {user_id}")

    # print(f"inlet: {json.dumps(data,indent=2)}")
    print(f"message to prompt\n{messages_to_prompt(messages)}")
    # print(data.get("body").get("task"))
    return data.get("body")


@app.route('/outlet', methods=["POST"])
def outlet():
    data = request.get_json()
    print(f"outlet: {data}")
    return data.get("body")


@app.route('/pipe', methods=["POST"])
def pipe():
    data = request.get_json()
    print(f"pipe: {data}")
    return data.get("body")


@app.route('/test', methods=["GET"])
def test():
    return {"res": True}


if __name__ == '__main__':
    app.run(use_reloader=True, debug=True, host='0.0.0.0', port=PORT, threaded=True)
