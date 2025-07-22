import json


def read_file(file_path: str):
    with open(file_path, 'r') as file:
        content = file.read()
        return content


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
    parts = content.get("parts")
    if not parts:
        # print("no parts")
        return
    status = message.get("status")

    # if status == "finished_successfully":
    #     print("nice")

    if len(parts) > 0:
        print(f"{role}: {"\n".join(parts)}")


convo = read_file("../prompts/conversations.json")

convo_json = json.loads(convo)
print(json.dumps(convo_json, indent=2))

print(convo_json[0:1])

# for conversation in convo_json[0, 1]:
#     print(conversation.get("title"))

# for i, con in convo_json.items():
#     # for i in range(1):
#     data = con
#     # print(json.dumps(data, indent=2))
#     print(f'{i + 1}. {data.get("title")}')
#     # mapping = data.get("mapping")
#     # for key, value in mapping.items():
#     #     mapping_to_text(value)

# count = 1
# for con in convo_json:
#     print(f'{count}. {con.get("title")}')
#     count = count + 1
#     mapping = con.get("mapping")
#     mapping_to_text(mapping)
