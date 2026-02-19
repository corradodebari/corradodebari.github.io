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
    - export CONDUCTOR_SERVER_URL=http://localhost:7001/api

Usage:
    python examples/agentic_workflows/llm_chat_human_in_loop.py
"""

import json
import time

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.orkes_clients import OrkesClients
from conductor.client.worker.worker_task import worker_task
from conductor.client.workflow.conductor_workflow import ConductorWorkflow
from conductor.client.workflow.task.do_while_task import LoopTask
from conductor.client.workflow.task.llm_tasks.llm_chat_complete import LlmChatComplete, ChatMessage
from conductor.client.workflow.task.timeout_policy import TimeoutPolicy
from conductor.client.workflow.task.wait_task import WaitTask

from conductor.client.workflow.executor.workflow_executor import WorkflowExecutor
from conductor.client.http.models import StartWorkflowRequest, RerunWorkflowRequest, TaskResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o-mini"
SYSTEM_PROMPT = (
    "You are a helpful assistant that knows about science. "
    "Answer questions clearly and concisely. If you don't know "
    "something, say so. Stay on topic."
)

VERSION = 1

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

@worker_task(task_definition_name='human_chat_collect_history')
def collect_history(
    system_prompt: str = None,
    user_input: str = None,
    assistant_response: str = None,
    history: object = None,
) -> list:
    """Append the latest user and assistant messages to the conversation history.

    Handles the first loop iteration where unresolved references arrive as
    literal strings starting with '$'.
    """
    all_history = []

    if system_prompt and not isinstance(history, list):
        all_history.append({"role": "system", "message": system_prompt})

    if history and isinstance(history, list):
        for item in history:
            if isinstance(item, dict) and "role" in item and "message" in item:
                all_history.append(item)

    if assistant_response and not str(assistant_response).startswith("$"):
        all_history.append({"role": "assistant", "message": assistant_response})

    if user_input and not str(user_input).startswith("$"):
        all_history.append({"role": "user", "message": user_input})

    return all_history


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def create_human_chat_workflow(executor) -> ConductorWorkflow:
    wf = ConductorWorkflow(name="llm_chat_human_in_loop", version=1, executor=executor)

    # Wait for the user to type a question
    user_input = WaitTask(task_ref_name="user_input_ref")

    # Collect conversation history
    collect_history_task = collect_history(
        task_ref_name="collect_history_ref",
        user_input="${user_input_ref.output.question}",
        history="${chat_complete_ref.input.messages}",
        assistant_response="${chat_complete_ref.output.result}",
    )

    # Chat completion with system prompt passed inline
    chat_complete = LlmChatComplete(
        task_ref_name="chat_complete_ref",
        llm_provider=LLM_PROVIDER,
        model=LLM_MODEL,
        messages=[]
    )
    # Set messages as a dynamic reference (bypass constructor to avoid string iteration)
    chat_complete.input_parameters["messages"] = "${collect_history_ref.output.result}"

    # Loop: wait for user -> collect history -> respond
    loop_tasks = [user_input, collect_history_task, chat_complete]
    chat_loop = LoopTask(task_ref_name="loop", iterations=5, tasks=loop_tasks)

    wf >> chat_loop
    wf.timeout_seconds(300).timeout_policy(timeout_policy=TimeoutPolicy.TIME_OUT_WORKFLOW)

    return wf


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    api_config = Configuration()
    clients = OrkesClients(configuration=api_config)
    workflow_executor = clients.get_workflow_executor()
    workflow_client = clients.get_workflow_client()
    task_client = clients.get_task_client()

    import inspect
    print(inspect.signature(workflow_executor.start_workflow))

    # Start workers
    task_handler = TaskHandler(
        workers=[], configuration=api_config, scan_for_annotated_workers=True,
    )
    task_handler.start_processes()

    try:
        we = workflow_executor  
        req = StartWorkflowRequest(name="llm_chat_human_in_loop",version=VERSION,input={},correlation_id="correlation_123")
        workflow_id = we.start_workflow(req)
       
        print(f"Started: {workflow_id}")

        workflow_run=workflow_client.get_workflow(workflow_id=workflow_id,include_tasks=True)

        print("Interactive science chat (type 'quit' to exit)")
        print("=" * 50)

        print(f"\nWorkflow details: {api_config.ui_host}/api/workflow/{workflow_id}")

        while workflow_run.is_running():
            current = workflow_run.current_task
            if current and current.workflow_task.task_reference_name == "user_input_ref":
                # Show the previous assistant response if available
                assistant_task = workflow_run.get_task(task_reference_name="chat_complete_ref")
                if assistant_task and assistant_task.output_data.get("response"):
                    print(f"Assistant: {assistant_task.output_data['response'].strip()}\n")

                # Get user input
                question = input("You: ")
                if question.lower() in ("quit", "exit", "q"):
                    print("\nEnding conversation.")
                    workflow_client.terminate_workflow(workflow_id)
                    break

                # Complete the WAIT task with user's question
                task_client.update_task_sync(
                    workflow_id=workflow_id,
                    task_ref_name="user_input_ref",
                    status=TaskResultStatus.COMPLETED,
                    output={"question": question},
                )

            time.sleep(0.5)
            workflow_run = workflow_client.get_workflow(workflow_id=workflow_id, include_tasks=True)

        # Show final assistant response
        if workflow_run.is_completed():
            assistant_task = workflow_run.get_task(task_reference_name="chat_complete_ref")
            if assistant_task and assistant_task.output_data.get("response"):
                print(f"Assistant: {assistant_task.output_data['response'].strip()}")

        print(f"\nFull conversation: {api_config.ui_host}/api/workflow/{workflow_id}")

        assistant_task = workflow_run.get_task(task_reference_name="chat_complete_ref")
        if assistant_task and assistant_task.input_data.get("prompt"):
            last_message={"role":"assistant","message":assistant_task.output_data["response"]}
            assistant_task.input_data['prompt'].append(last_message)
            
            print(f"Conversation History: {json.dumps(assistant_task.input_data['prompt'], indent=2)}")

    finally:
        task_handler.stop_processes()


if __name__ == "__main__":
    main()