from pathlib import Path

# directory loading
def load_base_directory():
    try:
        BASE_DIR = Path(__file__).resolve().parent
    except NameError:
        BASE_DIR = Path.cwd()
    return BASE_DIR 


BASE_DIR = load_base_directory()
CONTEXT_DIR = BASE_DIR / "context" 
CONTEXT_DIR.mkdir(exist_ok=True) # create directory if not already created
INDEX_DIR = BASE_DIR / "vectorstore"
INDEX_DIR.mkdir(exist_ok=True)