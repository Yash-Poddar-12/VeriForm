from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio

app = FastAPI(title="VeriForm Hostile Benchmark Server")

# Resolve the hostile_benchmark_suite directory relative to THIS file
_this_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.normpath(os.path.join(_this_dir, "..", "hostile_benchmark_suite"))

if not os.path.isdir(static_dir):
    raise RuntimeError(f"hostile_benchmark_suite directory not found at: {static_dir}")

# Mount HTML files directly at root "/" so:
#   http://127.0.0.1:8000/optimistic_ui.html  → serves the file
# Must be mounted AFTER explicit route registrations to avoid shadowing them.

@app.get("/")
def index():
    return HTMLResponse("<h1>VeriForm Benchmark Server Running</h1>")

@app.get("/trigger_400")
async def trigger_400():
    """Artificial 400 endpoint with latency to stress-test SyncManager network idle logic."""
    await asyncio.sleep(0.5)
    return JSONResponse(status_code=400, content={"error": "Validation rejected by backend"})

# Register static mount at "/" AFTER explicit routes so /trigger_400 takes priority.
app.mount("/", StaticFiles(directory=static_dir, html=True), name="benchmarks")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
