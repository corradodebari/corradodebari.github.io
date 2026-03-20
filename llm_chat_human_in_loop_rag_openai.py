"""
LLM Chat with Human-in-the-Loop

Demonstrates an interactive chat where the workflow pauses for user input
between LLM responses using Conductor's WAIT task. The user types questions
in the terminal, and the LLM responds, maintaining conversation history.

Pipeline:
    loop(wait_for_user --> collect_history --> chat_complete) --> summary

Requirements:
    - Conductor server with AI/LLM support
    - LLM provider named 'openai' with a valid API key configured
    - export MICROTX_WORKFLOW_SERVER_URL=http://localhost:7001/api

Usage:
    python examples/agentic_workflows/llm_chat_human_in_loop.py
"""

import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.orkes_clients import OrkesClients
from conductor.client.worker.worker_task import worker_task
from conductor.client.http.models import StartWorkflowRequest

# ---------------------------------------------------------------------------
# Configuration: config.json defaults, env variables override
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_file_cfg = {}
if os.path.exists(_config_path):
    with open(_config_path) as _f:
        _file_cfg = json.load(_f)
    logger.info("Loaded config from %s", _config_path)

LLM_MODEL = os.getenv("LLM_MODEL", _file_cfg.get("LLM_MODEL", "microtx"))
WORKFLOW_NAME = os.getenv("WORKFLOW_NAME", _file_cfg.get("WORKFLOW_NAME", "llm_chat_openai_api"))
VERSION = int(os.getenv("WORKFLOW_VERSION", _file_cfg.get("WORKFLOW_VERSION", 2)))
INPUT_TASK = os.getenv("INPUT_TASK", _file_cfg.get("INPUT_TASK", "user_input_ref"))
OUTPUT_TASK = os.getenv("OUTPUT_TASK", _file_cfg.get("OUTPUT_TASK", "chat_complete_ref"))

# Idle timeout (seconds): terminate workflows if no requests within this period
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", _file_cfg.get("IDLE_TIMEOUT", 300)))

# KEYS_WORKFLOWS: env var as JSON string, or from config file
_keys_env = os.getenv("KEYS_WORKFLOWS")
if _keys_env:
    KEYS_WORKFLOWS = json.loads(_keys_env)
else:
    KEYS_WORKFLOWS = _file_cfg.get("KEYS_WORKFLOWS", {"ABC12345": "", "ABC67890": ""})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Map MICROTX_WORKFLOW_SERVER_URL to CONDUCTOR_SERVER_URL for the SDK
    microtx_url = os.getenv("MICROTX_WORKFLOW_SERVER_URL")
    if microtx_url:
        os.environ["CONDUCTOR_SERVER_URL"] = microtx_url

    api_config = Configuration()
    clients = OrkesClients(configuration=api_config)
    workflow_executor = clients.get_workflow_executor()
    workflow_client = clients.get_workflow_client()
    task_client = clients.get_task_client()

    # Start workers
    task_handler = TaskHandler(
        workers=[], configuration=api_config, scan_for_annotated_workers=True,
    )
    task_handler.start_processes()

    # Track last request time per API key
    last_activity = {}

    async def idle_monitor():
        """Periodically check for idle workflows and terminate them."""
        while True:
            await asyncio.sleep(60)  # check every 60 seconds
            now = time.time()
            for api_key, workflow_id in list(KEYS_WORKFLOWS.items()):
                if not workflow_id:
                    continue
                last_time = last_activity.get(api_key, 0)
                if last_time > 0 and (now - last_time) > IDLE_TIMEOUT:
                    try:
                        await asyncio.to_thread(workflow_client.terminate_workflow, workflow_id)
                        logger.info("Terminated idle workflow %s for key %s (idle %.0fs)",
                                    workflow_id, api_key, now - last_time)
                    except Exception:
                        logger.warning("Failed to terminate idle workflow %s", workflow_id)
                    KEYS_WORKFLOWS[api_key] = ""
                    last_activity.pop(api_key, None)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(idle_monitor())
        yield
        task.cancel()

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(">>> %s %s", request.method, request.url.path)
        response = await call_next(request)
        logger.info("<<< %s %s -> %s", request.method, request.url.path, response.status_code)
        return response

    @app.get("/v1/models")
    def list_models():
        return JSONResponse(content={
            "object": "list",
            "data": [
                {
                    "id": LLM_MODEL,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "conductor",
                }
            ],
        })

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
      try:
        body = await request.json()
        # Extract the API key from the Authorization header
        auth_header = request.headers.get("Authorization", "")
        MICROTX_API_KEY = auth_header[len("Bearer "):] if auth_header.startswith("Bearer ") else ""

        # Validate API key against KEYS_WORKFLOWS dictionary
        logger.info("API key received: %s", MICROTX_API_KEY)
        if MICROTX_API_KEY not in KEYS_WORKFLOWS:
            raise HTTPException(status_code=401, detail="Invalid API key")

        messages = body.get("messages", [])

        # Track activity for idle timeout
        last_activity[MICROTX_API_KEY] = time.time()

        # Check if MICROTX_API_KEY in KEYS_WORKFLOWS
        start_new = True
        if MICROTX_API_KEY in KEYS_WORKFLOWS and KEYS_WORKFLOWS[MICROTX_API_KEY]:
            # Verify the existing workflow is still running
            workflow_id = KEYS_WORKFLOWS[MICROTX_API_KEY]
            try:
                existing_run = await asyncio.to_thread(
                    workflow_client.get_workflow, workflow_id=workflow_id, include_tasks=False
                )
                if existing_run.is_running():
                    start_new = False
                    logger.info("Reusing existing workflow: %s", workflow_id)
                else:
                    logger.warning("Previous workflow %s is no longer running, starting new one", workflow_id)
            except Exception:
                logger.warning("Could not retrieve workflow %s, starting new one", workflow_id)

        if start_new:
            # Start a new workflow instance
            correlation_id = str(uuid.uuid4())
            req = StartWorkflowRequest(
                name=WORKFLOW_NAME, version=VERSION, input={}, correlation_id=correlation_id
            )
            workflow_id = await asyncio.to_thread(workflow_executor.start_workflow, req)
            logger.info("Started new workflow: %s", workflow_id)
            # Store workflow_id for this API key
            KEYS_WORKFLOWS[MICROTX_API_KEY] = workflow_id

        # Wait until the workflow reaches the WAIT task (user_input_ref)
        while True:
            workflow_run = await asyncio.to_thread(
                workflow_client.get_workflow, workflow_id=workflow_id, include_tasks=True
            )
            current = workflow_run.current_task
            if current and current.workflow_task.task_reference_name == INPUT_TASK:
                break
            if not workflow_run.is_running():
                raise HTTPException(status_code=500, detail="Workflow ended before reaching input task")
            await asyncio.sleep(0.3)

        # Capture the current OUTPUT_TASK update time BEFORE completing the WAIT task
        # so we can distinguish stale results from fresh ones
        prev_output_update_time = None
        workflow_run = await asyncio.to_thread(
            workflow_client.get_workflow, workflow_id=workflow_id, include_tasks=True
        )
        chat_task = workflow_run.get_task(task_reference_name=OUTPUT_TASK)
        if chat_task:
            prev_output_update_time = chat_task.update_time
            logger.debug("Previous OUTPUT_TASK update_time: %s", prev_output_update_time)

        # Forward the OpenAI messages to the WAIT task output
        await asyncio.to_thread(
            task_client.update_task_sync,
            workflow_id=workflow_id,
            task_ref_name=INPUT_TASK,
            status=TaskResultStatus.COMPLETED,
            output={"messages": messages},
        )
        logger.info("Messages forwarded to workflow")

        # Poll until OUTPUT_TASK produces a FRESH result (newer than the previous one)
        answer = ""
        while True:
            workflow_run = await asyncio.to_thread(
                workflow_client.get_workflow, workflow_id=workflow_id, include_tasks=True
            )
            chat_task = workflow_run.get_task(task_reference_name=OUTPUT_TASK)
            if chat_task and chat_task.output_data.get("response"):
                # Only accept if this is a new result (update_time changed)
                if prev_output_update_time is None or chat_task.update_time != prev_output_update_time:
                    answer = chat_task.output_data["response"]
                    break
            if not workflow_run.is_running():
                break
            await asyncio.sleep(0.3)

        # Keep workflow alive for reuse — only terminate if key is not tracked
        if MICROTX_API_KEY not in KEYS_WORKFLOWS or not KEYS_WORKFLOWS[MICROTX_API_KEY]:
            try:
                await asyncio.to_thread(workflow_client.terminate_workflow, workflow_id)
            except Exception:
                pass

        logger.info("Answer from workflow: %s...", answer[:100])

        # Check if client requested streaming
        stream = body.get("stream", False)
        completion_id = f"chatcmpl-{workflow_id}"
        created = int(time.time())

        if stream:
            def generate_stream():
                # First chunk: role
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": LLM_MODEL,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"

                # Stream content in word-sized chunks
                words = answer.split(" ")
                for i, word in enumerate(words):
                    token = word if i == 0 else f" {word}"
                    chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": LLM_MODEL,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                # Final chunk: finish_reason
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": LLM_MODEL,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate_stream(), media_type="text/event-stream")

        # Non-streaming: return full response
        return JSONResponse(content={
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": LLM_MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": answer,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        })
      except HTTPException:
        raise
      except Exception:
        logger.exception("Error in /v1/chat/completions")
        raise HTTPException(status_code=500, detail="Internal server error")

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        task_handler.stop_processes()


if __name__ == "__main__":
    main()