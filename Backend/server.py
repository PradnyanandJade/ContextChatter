from fastapi import FastAPI,UploadFile,File
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from database import create_database,insert_document,get_document,delete_document,get_all_documents
from load_directory import CONTEXT_DIR
from models.ChatRequest import ChatRequest
import uuid
import shutil
from rag_agent import agent,add_document_to_vectorstore,rebuild_index,initialize_vectorstore

# app
app = FastAPI()
# static files 
app.mount("/context",StaticFiles(directory=CONTEXT_DIR),name="context")


# create db if not exist
create_database()

# first create database
initialize_vectorstore()

# Rest api
@app.get('/')
def home():
    """ This is the default endpoint of api """
    return "Welcome to ContextChatter fastapi"


# ====================================================== file management =====================================================
def format_filename(filename:str):
    return filename.replace(' ','_')

@app.get('/files')
def get_all_files():
    return get_all_documents()


@app.post('/files/upload')
def upload_file(file : UploadFile = File(...)):
    """This uploads and saves the file to context directory"""
    formatted_filename = format_filename(file.filename)
    file_path = CONTEXT_DIR / formatted_filename
    with open(file_path,"wb") as buffer:
        shutil.copyfileobj(file.file,buffer)

    document_id = str(uuid.uuid4())
    insert_document(
        document_id=document_id,
        filename=formatted_filename,
        path=str(file_path)
    )
    add_document_to_vectorstore(
        document_id=document_id,
        filename=formatted_filename,
        path=str(file_path)
    )
    return {
        "message": "PDF uploaded successfully",
        "document_id":document_id,
        "filename": formatted_filename,
        "url":f"/context/{formatted_filename}"
    }

@app.delete('/files/{document_id}')
def delete_document_by_id(document_id:str):
    document = get_document(document_id)
    if document is None:
        return {
            "message":"Document not found"
        }
    
    file_path = Path(document["path"])

    if file_path.exists():
        file_path.unlink() # deletes file

    delete_document(document_id)
    rebuild_index()
    return {
        "message": "Document deleted successfully"
    }

# ====================================================== RAG MANAGEMENT =====================================================

@app.post('/chat')
def chat_with_context(chatRequest : ChatRequest):
    result_state = agent.invoke({
        'query' : chatRequest.query,
        'document_ids':chatRequest.document_ids
    })
    return result_state