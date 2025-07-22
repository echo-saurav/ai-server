import json


def read_file(file_path: str):
    with open(file_path, 'r') as file:
        content = file.read()
        return content


def count_data():
    data = read_file("./prompts/conversations.json")
    data = json.loads(data)
    return len(data)


print(count_data())
