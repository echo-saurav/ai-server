import json
import os
from pydantic import BaseModel
from flask import Flask, Response
from flask_cors import CORS
from flask import request
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models
from ollama import Client
from datetime import datetime, timezone, timedelta
import time

from ContextManager import ContextManager

# load all config
load_dotenv()
PORT = os.getenv(key='PORT', default=5500)
LOCAL_OLLAMA_HOST = os.getenv(key='LOCAL_OLLAMA_HOST', default="")
EMBEDDING_MODEL = os.getenv(key='EMBEDDING_MODEL', default="")
QDRANT_HOST = os.getenv(key='QDRANT_HOST', default="")
QDRANT_PORT = os.getenv(key='QDRANT_PORT', default="")
CHAT_COLLECTION_NAME = os.getenv(key='CHAT_COLLECTION_NAME', default='Chats')
OBSIDIAN_COLLECTION_NAME = os.getenv(key='COLLECTION_NAME', default='PluginDev')
CHAT_MODEL = os.getenv(key='CHAT_MODEL', default="gemma-3n-e4b-it")
CHAT_API = os.getenv(key='CHAT_API', default="https://generativelanguage.googleapis.com/v1beta/openai/")
CHAT_API_KEY = os.getenv(key='CHAT_API_KEY', default="AIzaSyAEAdGzqZ-5lbspw_SusP_9nXUt0QuBtv0")

# Flask App setup ____________________________________________________
app = Flask(__name__)
cors = CORS(app, origins="*")

# AI
context_manager = ContextManager(
    LOCAL_OLLAMA_HOST,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
    OBSIDIAN_COLLECTION_NAME,
    CHAT_COLLECTION_NAME
)


# API endpoints ____________________________________________________
@app.route('/inlet', methods=["POST"])
def inlet():
    data = request.get_json()
    print(f"inlet: {json.dumps(data, indent=2)}")
    body = data.get("body")
    metadata = body.get("metadata")
    user_id = metadata.get("user_id")
    email = metadata.get("email")
    task = metadata.get("task")
    messages = body.get("messages")

    if not task and messages:
        # alter messages and context
        context = context_manager.get_context(messages)
        # inject
        data.get("body").get("messages").insert(
            0, {"role": "user", "content": context}
        )
    return data.get("body")


@app.route('/outlet', methods=["POST"])
def outlet():
    data = request.get_json()
    print(f"outlet: {json.dumps(data, indent=2)}")
    body = data.get("body")
    uid = data.get("user").get("id")
    email = data.get("user").get("email")
    name = data.get("user").get("name")
    chat_id = body.get("chat_id")
    messages = body.get("messages")
    # run background tasks here

    return body


@app.route('/test', methods=["GET"])
def test():
    return {"res": True}


if __name__ == '__main__':
    app.run(use_reloader=True, debug=True, host='0.0.0.0', port=PORT, threaded=True)

