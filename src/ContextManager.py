from ollama import Client
from qdrant_client import QdrantClient, models


class ContextManager:
    def __init__(self, LOCAL_OLLAMA_HOST, EMBEDDING_MODEL, QDRANT_HOST, QDRANT_PORT, OBSIDIAN_COLLECTION_NAME,
                 CHAT_COLLECTION_NAME):
        self.LOCAL_OLLAMA_HOST = LOCAL_OLLAMA_HOST
        self.EMBEDDING_MODEL = EMBEDDING_MODEL
        self.QDRANT_HOST = QDRANT_HOST
        self.QDRANT_PORT = QDRANT_PORT
        self.OBSIDIAN_COLLECTION_NAME = OBSIDIAN_COLLECTION_NAME
        self.CHAT_COLLECTION_NAME = CHAT_COLLECTION_NAME

        self.ollamaClient = Client(LOCAL_OLLAMA_HOST)
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))

    def get_context(self, messages):
        messages_prompt = self.messages_to_prompt(messages)
        conversations = self.query_conversation(messages_prompt)
        notes = self.query_obsidian(messages_prompt)
        return self.populate_prompt(notes, conversations)

    def read_file(self, file_path: str):
        with open(file_path, 'r') as file:
            content = file.read()
            return content

    def populate_prompt(self, notes, conversations):
        context_prompt_template = self.read_file("../prompts/context_prompt.md")
        prompt = context_prompt_template.replace("{{notes}}", notes)
        prompt = prompt.replace("{{conversation}}", conversations)
        return prompt

    def query_conversation(self, prompt):
        embeddings = self.ollamaClient.embed(model=self.EMBEDDING_MODEL, input=prompt)
        embedding = embeddings.embeddings[0]
        hits = self.qdrant.query_points(
            collection_name=self.CHAT_COLLECTION_NAME,
            query=embedding,
            using="description",
            score_threshold=.5,
            limit=10,
            # query_filter={}
        )
        description = ""
        for point in hits.points:
            d = point.payload.get("description")
            description = f"{d}\n\n{description}"

        if description:
            return description
        else:
            return "No related chat found"

    def query_obsidian(self, prompt: str):
        embeddings = self.ollamaClient.embed(model=self.EMBEDDING_MODEL, input=prompt)
        embedding = embeddings.embeddings[0]
        hits = self.qdrant.query_points(
            collection_name=self.OBSIDIAN_COLLECTION_NAME,
            query=embedding,
            score_threshold=.5,
            limit=10,
            # query_filter={}
        )

        notes = ""
        for item in hits.points:
            notes = f'{notes}\n{item.payload.get("content")}\n'

        if notes:
            return notes
        else:
            return "No related notes found"

    def messages_to_prompt(self, messages):
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

    def inject_context(self, context, messages):
        print("all")

    def test(self):
        return  "nice"