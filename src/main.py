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

load_dotenv()
PORT = os.getenv(key='PORT', default=5500)
OLLAMA_HOST = os.getenv(key='LOCAL_OLLAMA_HOST', default="")
EMBEDDING_MODEL = os.getenv(key='EMBEDDING_MODEL', default="")
QDRANT_HOST = os.getenv(key='QDRANT_HOST', default="")
QDRANT_PORT = os.getenv(key='QDRANT_PORT', default="")
COLLECTION_NAME = os.getenv(key='COLLECTION_NAME', default='Chats')
OBSIDIAN_COLLECTION_NAME = os.getenv(key='COLLECTION_NAME', default='PluginDev')
CHAT_MODEL = os.getenv(key='CHAT_MODEL', default="gemma-3n-e4b-it")
CHAT_API = os.getenv(key='CHAT_API', default="https://generativelanguage.googleapis.com/v1beta/openai/")
CHAT_API_KEY = os.getenv(key='CHAT_API_KEY', default="AIzaSyAEAdGzqZ-5lbspw_SusP_9nXUt0QuBtv0")

# Flask App setup ____________________________________________________
app = Flask(__name__)
cors = CORS(app, origins="*")

# AI stuff ___________________________________________________________
qdrant = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
ollama = Client(host=OLLAMA_HOST)


def read_file(file_path: str):
    with open(file_path, 'r') as file:
        content = file.read()
        return content


def create_collection():
    if not qdrant.collection_exists(COLLECTION_NAME):
        print("create collection")
        qdrant.create_collection(
            COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
        )
    else:
        print("collection existed")


def create_summery(prompt: str):
    system_prompt = read_file("../prompts/chat_summery.md")
    openai = OpenAI(base_url=CHAT_API, api_key=CHAT_API_KEY)

    content = f"{system_prompt}\n{prompt}"

    response = openai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "user", "content": content}
        ]
    )

    summery = response.choices[0].message.content
    return summery


def insert_chat_summery(summery, chat_id, body):
    print(summery)
    embeddings = ollama.embed(model=EMBEDDING_MODEL, input=summery)
    embedding = embeddings.embeddings[0]

    points = {
        "ids": [chat_id],
        "payload": {
            "summery": summery,
            "body": body
        },
        "vectors": [
            embedding
        ]
    }
    # qdrant.upsert(COLLECTION_NAME, points)


def query_obsidian(prompt: str):
    embeddings = ollama.embed(model=EMBEDDING_MODEL, input=prompt)
    embedding = embeddings.embeddings[0]
    hits = qdrant.query_points(
        collection_name=OBSIDIAN_COLLECTION_NAME,
        query=embedding,
        score_threshold=.7,
        limit=10,
        # query_filter={}
    )
    if len(hits.points) == 0:
        return None

    results = ""
    for item in hits.points:
        results = f'{results}\n{item.payload.get("content")}\n{"-" * 20}\n'

    return results


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
    print(f"inlet: {json.dumps(data, indent=2)}")
    body = data.get("body")
    metadata = body.get("metadata")
    user_id = metadata.get("user_id")
    email = metadata.get("email")
    task = metadata.get("task")
    messages = body.get("messages")

    if user_id != "42b588b7-d006-43b6-8dc9-3186da84d651" and email != "saurav@email.com":
        return data.get("body")

    if not task and messages:
        query_prompt = messages_to_prompt(messages)
        similar_notes = query_obsidian(query_prompt)
        if similar_notes:
            contexts = f"Here is related contexts from user's notes, only answer from here if its relevant otherwise ignore these context\n<notes>{similar_notes}</notes>"
            print(contexts)

            data.get("body").get("messages").insert(
                0, {"role": "user", "content": contexts}
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

    print(f"uid: {uid}\nemail: {email}\nname: {name}\nchat_id:{chat_id}")

    messages_as_prompt = messages_to_prompt(messages)
    print(f"Message Prompt: {messages_as_prompt}")
    prompt = create_summery(messages_as_prompt)
    insert_chat_summery(prompt, chat_id, body)
    return body


@app.route('/pipe', methods=["POST"])
def pipe():
    data = request.get_json()
    print(f"pipe: {data}")
    return data.get("body")


@app.route('/test', methods=["GET"])
def test():
    return {"res": True}


def mapping_to_text(mapping):
    message = mapping.get("message")
    if not message:
        # print("no message")
        return
    author = message.get("author")
    if not author:
        # print("no author")
        return
    role = author.get("role")
    if not role:
        # print("no role")
        return

    if role not in ("user", "assistant"):
        return

    created_time = message.get("created_time")
    #
    content = message.get("content")
    if not content:
        # print("no content")
        return
    content_type = content.get("content_type")
    if not content_type:
        # print("no content type")
        return
    if content_type != "text":
        return
    parts = content.get("parts")
    if not parts:
        # print("no parts")
        return
    status = message.get("status")

    # if status == "finished_successfully":
    #     print("nice")

    if len(parts) > 0:
        # print(f"{role}: {"\n".join(parts)}")
        return f"{role}: {"\n".join(parts)}"


class Description(BaseModel):
    description: str
    chat_flow: str
    tags: list[str]


def testPrompt():
    content = read_file("../prompts/test.md")
    openai = OpenAI(base_url=CHAT_API, api_key=CHAT_API_KEY)

    class Summery(BaseModel):
        summery: str
        tags: list[str]

    res = openai.responses.parse(
        model=CHAT_MODEL,
        input=[
            {"role": "user", "content": content}
        ],
        text_format=Summery
    )
    print(res.output_parsed)


def openai_local(text: str):
    # openai = OpenAI(base_url=CHAT_API, api_key=CHAT_API_KEY)
    # openai = OpenAI(base_url="http://192.168.0.120:11434/v1", api_key=CHAT_API_KEY)
    openai = OpenAI(base_url="http://192.168.0.102:1234/v1", api_key=CHAT_API_KEY)

    response = openai.chat.completions.create(
        # model=CHAT_MODEL,
        model="jan-nano-128k",
        # model="lucy-128k-dq68-mlx",
        # model="gemma-3n-e2b-it-text",
        # model="gemma3n:e2b",
        # model="gemma-3n-e4b-it",
        # model="gemma-3n-e4b",
        messages=[
            {"role": "user", "content": text}
        ],
        max_tokens=128000,

    )

    return response.choices[0].message.content


def local(text: str):
    client = Client(host="http://192.168.0.120:11434")
    res = client.chat(
        messages=[
            {"role": "user", "content": text}
        ],
        # model="llama3.2:1b",
        model="llama3.2:latest",
    )
    # print(res.message.content)
    return res.message.content


def testPrompt2():
    convo = read_file("../prompts/conversations.json")
    convo_json = json.loads(convo)
    # print(json.dumps(convo_json, indent=2))

    prompt = ""
    index = 11
    for conversation in convo_json[index:index + 1]:
        print(conversation.get("title"))

        # extract messages
        mapping = conversation.get("mapping")
        for key, value in mapping.items():
            text = mapping_to_text(value)
            if text:
                prompt = f"{prompt}\n{text}"

    # print(prompt)

    content = read_file("../prompts/chat_summery2.md")
    tags = read_file("../prompts/tags.json")
    tags = json.loads(tags)
    tags = tags.get("tags")
    # content = read_file("../prompts/graph.md")
    replace_prompt = content.replace("{{text}}", prompt)
    replace_prompt = replace_prompt.replace("{{tags}}", ", ".join(tags))
    # print(content)
    # ollama = Client(host=OLLAMA_HOST)
    # res = ollama.chat(
    #     messages=[
    #         {"role": "user", "content": replace_prompt}
    #     ],
    #     # model="llama3.2:1b",
    #     model="llama3.2:latest",
    #     format=Summery.model_json_schema()
    # )
    # print(res.model_validate_json(res.message.content))
    # print(res.message.content)

    # print(replace_prompt)
    summery = openai_local(replace_prompt)
    # summery = local(replace_prompt)

    json_summery = summery.replace("json", "")
    json_summery = json_summery.replace("```", "")
    json_summery = json_summery.strip()
    print(json_summery)
    json_summery = json.loads(json_summery)

    print(f"summery: {json_summery.get('description')}")
    print(f"chat_flow: {json_summery.get('chat_flow')}")
    print(f"tags: {json_summery.get('tags')}")
    print(f"reaction: {json_summery.get('reaction')}")
    print(f"emotions: {json_summery.get('emotions')}")
    print(f"information: {json_summery.get('information')}")


def gen_description(prompt: str):
    # print(categories)
    content = read_file("../prompts/chat_summery2.md")
    replace_prompt = content.replace("{{text}}", prompt)
    replace_prompt = replace_prompt.replace("{{categories}}", get_categories())
    # print(replace_prompt)
    try:
        summery = openai_local(replace_prompt)
    except:
        return None
    json_summery = summery.replace("json", "")
    json_summery = json_summery.replace("```", "")
    json_summery = json_summery.strip()
    # print(json_summery)
    try:
        json_summery = json.loads(json_summery)
    except:
        return None

    return json_summery


def gen_analysis(prompt: str):
    content = read_file("../prompts/analysis_user.md")
    replace_prompt = content.replace("{{conversations}}", prompt)
    res = openai_local(replace_prompt)
    print(res)


def delete_chat_collection():
    if qdrant.collection_exists("Chats"):
        qdrant.delete_collection("Chats")


def create_chat_collection():
    if not qdrant.collection_exists("Chats"):
        print("create collection")
        qdrant.create_collection(
            "Chats",
            # vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
            vectors_config={
                "description": models.VectorParams(size=768, distance=models.Distance.COSINE),
                "chat_flow": models.VectorParams(size=768, distance=models.Distance.COSINE),
                "information": models.VectorParams(size=768, distance=models.Distance.COSINE),
                "prompt": models.VectorParams(size=768, distance=models.Distance.COSINE)
            }
        )
    else:
        print("collection existed")


def messages_from_mapping(mapping):
    prompt = ""
    for key, value in mapping.items():
        text = mapping_to_text(value)
        if text:
            prompt = f"{prompt}\n{text}"
    return prompt


def save_data(data):
    with open("../prompts/data.json", 'w') as file:
        file.write(json.dumps(data))


def push_desc(item):
    with open("../prompts/data.json", 'r') as file:
        try:
            old_data = json.loads(file.read())
        except:
            data = {"chats": []}
    old_data.get("chats").extend([item])

    with open("../prompts/data.json", 'w') as file:
        file.write(json.dumps(old_data, indent=2))


def get_categories():
    categories = read_file("../prompts/categories.json")
    categories = json.loads(categories)
    categories = categories.get("categories")
    return ", ".join(categories)


# def save_categories(new_categories):
#     if not new_categories:
#         return
#     new_categories = [new_category.strip() for new_category in new_categories if new_category.strip()]
#
#     old_categories = read_file("../prompts/tags.json")
#     old_categories = json.loads(old_categories)
#     old_categories = old_categories.get("categories", [])
#     # Merge and deduplicate
#     combined_tags = list(set(old_categories + new_categories))
#
#     with open("../prompts/tags.json", 'w') as file:
#         json.dump({"categories": combined_tags}, file, indent=2)
#

def count_data():
    data = read_file("../prompts/data.json")
    data = json.loads(data)
    chats = data.get("chats")
    return len(chats)


def sync_chatgpt():
    data_ = []
    convo = read_file("../prompts/conversations.json")
    convo_json = json.loads(convo)
    index = 2

    total_start = time.perf_counter()

    start = count_data() - 1
    print(f"start from index: {start}")
    count = start

    for conversation in convo_json[start:]:
        loop_start = time.perf_counter()
        created = conversation.get("create_time")
        updated = conversation.get("update_time")
        update_time = datetime.fromtimestamp(updated, tz=timezone(timedelta(hours=6)))
        update_time = update_time.strftime("%Y-%m-%d %I:%M:%p")

        print(f"{count}. {conversation.get('title')} {update_time}")
        prompt = ""
        mapping = conversation.get("mapping")

        # print(json.dumps(mapping,indent=2))
        prompt = messages_from_mapping(mapping)
        desc = gen_description(prompt)
        if desc:
            print(desc)
            # categories = desc.get("categories")
            # save_categories(categories)
            data_point = {
                "desc": desc,
                "prompt": prompt,
                "updated": updated,
                "created": created
            }
            # data_.append(data_point)
            push_desc(data_point)

            # count time
            # current loop time
            # loop_end = time.perf_counter()
            # duration_min = (loop_end - loop_start) / 60
            # print(f"Time: {duration_min:.4f} minute")
            # # total time
            # total_end = time.perf_counter()
            # total_duration_min = (total_end - total_start) / 60
            # print(f"Total time: {total_duration_min:.4f} minute")

        else:
            data_point = {
                "prompt": prompt,
                "updated": updated,
                "created": created
            }
            push_desc(data_point)
            print(f"skip: {conversation.get('title')}")
            print(desc)
            continue

        count = count + 1
        print("wait 10 sec")
        time.sleep(10)
    #
    # json list
    # data_ = {"chats": data_}
    # print(json.dumps(data_, indent=2))
    # save_data(data_)
    print("DONE!")

    # print(prompt)

    # print(prompt)

    # print(json.dumps(conversation,indent=2))


# sync_chatgpt()
# print(count_data())
# testPrompt2()

def time_ago(ts):
    now = datetime.now(timezone(timedelta(hours=6)))
    dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=6)))
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def analysis_user():
    data = read_file("../prompts/data.json")
    data = json.loads(data)
    chats = data.get("chats")
    descriptions = []
    prompt = ""
    for chat in chats[0:60]:
        # print(chat)
        desc = chat.get("desc", {})
        description = desc.get("description")
        chat_flow = desc.get("chat_flow")

        if desc and chat_flow:
            updated = chat.get("updated")
            ago = time_ago(updated)
            # prompt = f"{prompt}\n\n\n{ago}:\n\n{description}\n"
            prompt = f"{prompt}\n\n\n{ago}:\n\n{'\n'.join(chat_flow)}\n"

    print(prompt)
    gen_analysis(prompt)

    # print("\n\n".join(descriptions))


def get_ollama_embed(text: str):
    embeddings = ollama.embed(model=EMBEDDING_MODEL, input=text)
    embedding = embeddings.embeddings[0]
    return embedding


def upload_qdrant(vid, payload, description, chat_flow, information, prompt):
    qdrant.upsert(
        collection_name="Chats",
        wait=True,
        points=[
            models.PointStruct(
                id=vid,
                vector={
                    "description": description,
                    "chat_flow": chat_flow,
                    "information": information,
                    "prompt": prompt
                },
                payload=payload
            )
        ]
    )


def upload_vector():
    delete_chat_collection()
    create_chat_collection()
    data = read_file("../prompts/data.json")
    data = json.loads(data)
    chats = data.get("chats")
    count = 1
    for chat in chats:
        desc = chat.get("desc", {})

        description = desc.get("description", None)
        chat_flow = desc.get("chat_flow", None)
        tags = desc.get("tags", None)
        categories = desc.get("categories", None)
        prompt = chat.get("prompt", None)
        reactions = desc.get("reactions", None)
        emotions = desc.get("emotions", None)
        information = desc.get("information", None)
        updated = chat.get("updated", None)

        if description:
            description_v = get_ollama_embed(f"search_document: {description}")
            chat_flow_v = get_ollama_embed(f"search_document: {chat_flow}")
            information_v = get_ollama_embed(f"search_document: {information}")
            prompt_v = get_ollama_embed(f"search_document: {prompt}")

            payload = {
                "description": description,
                "chat_flow": chat_flow,
                "information": information,
                "prompt": prompt,
                "tags": tags,
                "categories": categories,
                "reactions": reactions,
                "emotions": emotions,
                "updated": updated
            }
            print(f"upload:{count}")

            upload_qdrant(count, payload, description_v, chat_flow_v, information_v, prompt_v)
            count = count + 1


def query(prompt: str):
    embed = get_ollama_embed(f"search_query: {prompt}")
    res = qdrant.query_points(
        "Chats",
        query=embed,
        using="description",
        limit=10
    )
    descriptions = []
    for point in res.points:
        d = point.payload.get("description")
        s = point.score
        descriptions.append(f"score: {s}\n{d}")
    return descriptions


running = True
while running:
    qus = input(">")
    res = query(f"user: {qus}")
    print("\n".join(res))

# analysis_user()
upload_vector()
# if __name__ == '__main__':
#     create_collection()
#     app.run(use_reloader=True, debug=True, host='0.0.0.0', port=PORT, threaded=True)
