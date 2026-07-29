
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated,Literal
from langchain_community.document_loaders import DirectoryLoader,PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage,BaseMessage
from langchain_huggingface import ChatHuggingFace,HuggingFaceEndpoint,HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from load_directory import INDEX_DIR
from database import get_all_documents
from dotenv import load_dotenv
import shutil
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

load_dotenv()

history = []

llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    task="text-generation"
)
model = ChatHuggingFace(llm=llm)

embedding = HuggingFaceEmbeddings(model='BAAI/bge-small-en-v1.5')

splitter = RecursiveCharacterTextSplitter(
            chunk_size = 1000,
            chunk_overlap = 200
        )


vectorstore = None

def rebuild_index():
    global vectorstore
    documents = get_all_documents()
    all_chunks = []
    for document in documents:
        loader = PyPDFLoader(document['path'])
        pages = loader.load()
        chunks = splitter.split_documents(pages)
        for chunk in chunks:
            chunk.metadata["document_id"] = document["document_id"]
            chunk.metadata["filename"] = document["filename"]
            chunk.metadata["path"] = document["path"]
        all_chunks.extend(chunks)
    

    if not all_chunks:
        vectorstore = None
        if (INDEX_DIR / 'vsindex').exists():
            shutil.rmtree(INDEX_DIR / 'vsindex')
        return

    vectorstore = FAISS.from_documents(all_chunks,embedding)
    vectorstore.save_local(str(INDEX_DIR / 'vsindex'))


def initialize_vectorstore():
    global vectorstore

    if (INDEX_DIR/"vsindex/index.faiss").exists():
        vectorstore = FAISS.load_local(
            INDEX_DIR / "vsindex",
            embedding,
            allow_dangerous_deserialization=True,
        )
    else:
        rebuild_index()



def add_document_to_vectorstore(document_id:str,filename:str,path:str):
    loader = PyPDFLoader(path)
    documents = loader.load()
    chunks = splitter.split_documents(documents)
    for chunk in chunks:
        chunk.metadata["document_id"] = document_id
        chunk.metadata["filename"] = filename
        chunk.metadata["path"] = path

    global vectorstore
    if vectorstore is None:
        vectorstore = FAISS.from_documents(chunks,embedding)
    else:
        vectorstore.add_documents(chunks)   
    vectorstore.save_local(INDEX_DIR/"vsindex")



def documents_to_text(documents):
    return "\n\n".join(
        f"""
        Source: {doc.metadata.get("filename")}
        Content:
        {doc.page_content}
        """
        for doc in documents
    )

class RagState(TypedDict):
    query : str 
    rewritten_query: str
    document_ids : list[str]
    context : list[Document]
    answer : str



rewrite_prompt = PromptTemplate(
    input_variables=["history", "query"],
    template="""
Rewrite the latest user question into a standalone question.

Rules:
- Preserve the original meaning.
- Resolve references such as "it", "they", "this", etc.
- Do NOT answer the question.
- Return ONLY the rewritten question.

Conversation History:
{history}

Latest User Question:
{query}

Standalone Question:
"""
)


def rewrite_query(state: RagState):
    history_text = "\n".join(
        f"{msg.type}: {msg.content}"
        for msg in history
    )

    prompt = rewrite_prompt.invoke({
        "history": history_text,
        "query": state["query"]
    })

    response = model.invoke(prompt)

    return {
        "rewritten_query": response.content.strip()
    }


def get_context(state : RagState):
    if vectorstore is None:
        return {
            "context": []
        }
    
    query = state['rewritten_query']
    document_ids = state['document_ids']
    documents = vectorstore.similarity_search(
        query=query,
        k=4,
        filter={
            "document_id":{
                "$in" : document_ids
            }
        }
    )
    return {
        'context' : documents
    }



answer_prompt = PromptTemplate(
    input_variables=[
        "history",
        "context",
        "query",
        "rewritten_query"
    ],
    template="""
You are a helpful AI assistant.

Use ONLY the retrieved context to answer.

Conversation History:
{history}

Retrieved Context:
{context}

Original User Question:
{query}

Standalone Question:
{rewritten_query}

If the context does not contain the answer, reply exactly:
"The provided context is not sufficient to answer this question."

Answer:
"""
)

def ask_query(state: RagState):

    if not state["context"]:
        return {
            "answer": "The provided context is not sufficient to answer this question.",
        }

    history_text = "\n".join(
        f"{msg.type}: {msg.content}"
        for msg in history
    )

    prompt = answer_prompt.invoke({
        "history": history_text,
        "context": documents_to_text(state["context"]),
        "query": state["query"],
        "rewritten_query": state["rewritten_query"]
    })

    response = model.invoke(prompt)

    history.append(HumanMessage(content=state["query"]))
    history.append(AIMessage(content=response.content))

    return {
        "answer": response.content
    }



graph = StateGraph(RagState)

graph.add_node("rewrite_query", rewrite_query)
graph.add_node("get_context", get_context)
graph.add_node("ask_query", ask_query)

graph.add_edge(START, "rewrite_query")
graph.add_edge("rewrite_query", "get_context")
graph.add_edge("get_context", "ask_query")
graph.add_edge("ask_query", END)

agent = graph.compile()
