from pydantic import BaseModel

class ChatRequest(BaseModel):
    query : str
    document_ids : list[str]