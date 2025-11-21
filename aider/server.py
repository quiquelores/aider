import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Mock audioop for Python 3.13+ compatibility if pydub fails
if sys.version_info >= (3, 13):
    try:
        import audioop
    except ImportError:
        import types
        sys.modules["audioop"] = types.ModuleType("audioop")
        sys.modules["pyaudioop"] = types.ModuleType("pyaudioop")

from aider.main import main as cli_main
from aider.coders import Coder
from aider.io_server import ServerIO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
coder: Optional[Coder] = None
server_io: Optional[ServerIO] = None

class ChatRequest(BaseModel):
    message: str

def get_coder():
    global coder, server_io
    if coder is None:
        # Initialize with default args, but capturing IO
        server_io = ServerIO()
        
        # Mocking sys.argv to ensure no interactive flags trigger unwanted behavior
        # and to force --yes-always for non-interactive server mode.
        original_argv = list(os.sys.argv)
        os.sys.argv = ["aider", "--yes-always", "--no-pretty"] 
        
        try:
            coder_or_status = cli_main(return_coder=True)
            if isinstance(coder_or_status, int):
                raise RuntimeError(f"Aider initialization failed with status code {coder_or_status}. Check logs.")
            
            coder = coder_or_status
            # Swap IO
            coder.io = server_io
            coder.commands.io = server_io
            
            # Force stream/yield
            coder.yield_stream = True
            coder.stream = True
            coder.pretty = False
            
        finally:
            os.sys.argv = original_argv
            
    return coder, server_io

@app.on_event("startup")
async def startup_event():
    get_coder()

def process_tool_output(item):
    content = item.get("content", "")
    
    if not content or not content.strip():
        return None
        
    # High-level status mapping
    if "Applied edit to" in content:
        return {"type": "status", "content": "Edited files..."}
    elif "Repo-map:" in content:
        return {"type": "status", "content": "Reading codebase..."}
    elif "tokens" in content.lower() and "cost" in content.lower():
        return {"type": "status", "content": "Finalized plan."}
    elif "Commit" in content:
        return {"type": "status", "content": "Saving changes..."}
    elif "run" in content.lower() and "output" in content.lower():
        # e.g. "Running python3 script.py"
        return {"type": "status", "content": "Running code..."}
    
    # If strictly abstracting, return None for everything else.
    # If you want to show errors, check for type="tool_error"
    if item.get("type") == "tool_error":
        return {"type": "error", "content": "Error: " + content}
        
    return None

@app.post("/chat")
async def chat(request: ChatRequest):
    coder, io = get_coder()
    if not coder:
        raise HTTPException(status_code=500, detail="Coder not initialized")

    message = request.message
    
    async def event_generator():
        # 1. Handle Commands
        if coder.commands.is_command(message):
            yield json.dumps({"type": "status", "content": "Executing command..."}) + "\n"
            coder.commands.run(message)
            while not io.output_queue.empty():
                item = io.output_queue.get()
                event = process_tool_output(item)
                if event:
                    yield json.dumps(event) + "\n"
            return

        # 2. Handle Chat
        yield json.dumps({"type": "status", "content": "Analyzing and Planning..."}) + "\n"
        
        # This generator yields chunks of text from the LLM
        for _ in coder.run_stream(message):
            # We discard the chunks (_) to hide code generation
            
            # Check tool outputs
            while not io.output_queue.empty():
                item = io.output_queue.get()
                event = process_tool_output(item)
                if event:
                    yield json.dumps(event) + "\n"
        
        # Final flush
        while not io.output_queue.empty():
            item = io.output_queue.get()
            event = process_tool_output(item)
            if event:
                yield json.dumps(event) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
