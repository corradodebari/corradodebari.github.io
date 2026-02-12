
# MicroTx Workflows: simple custom workers

In this tutorial, I'll show how to adapt the basic Python worker example [Python SDK](https://orkes.io/content/sdks/python) to the MicroTx Workflow platform, runnning in the env installed via the **Oracle Live Lab**: [Design and Deploy Agentic Workflows with Large Language Models and Distributed Transactions
](https://livelabs.oracle.com/ords/r/dbpm/livelabs/run-workshop?p210_wid=4243).

## Setup the environment
- Get the EXTERNAL_IP:
```shell
kubectl get svc -n istio-system
```

example:10.107.38.138

- Prepare the env and set the standard end-point for engine communication, slightly different by standard Conductor URL:

```shell
python3 -m venv conductor
source conductor/bin/activate

python3 -m pip install conductor-python

export CONDUCTOR_SERVER_URL=http://10.107.38.138/workflow-server/api  
```

## Install the example workflow

Prepare and create a new workflow based on the `simple_worker.json` with:
```json

{
  "name": "simple_worker",
  "description": "Sample workflow calling simple workers",
  "version": 1,
  "tasks": [
    {
      "name": "get_name",
      "taskReferenceName": "get_name_ref",
      "inputParameters": {
        "name": "${workflow.input.name}"
      },
      "type": "SIMPLE",
      "decisionCases": {},
      "defaultCase": [],
      "forkTasks": [],
      "startDelay": 0,
      "joinOn": [],
      "optional": false,
      "defaultExclusiveJoinTask": [],
      "asyncComplete": false,
      "loopOver": [],
      "onStateChange": {},
      "permissive": false
    },
    {
      "name": "get_id",
      "taskReferenceName": "get_id_ref",
      "inputParameters": {
        "id": "${workflow.input.name}"
      },
      "type": "SIMPLE",
      "decisionCases": {},
      "defaultCase": [],
      "forkTasks": [],
      "startDelay": 0,
      "joinOn": [],
      "optional": false,
      "defaultExclusiveJoinTask": [],
      "asyncComplete": false,
      "loopOver": [],
      "onStateChange": {},
      "permissive": false
    }
  ],
  "inputParameters": [],
  "outputParameters": {},
  "schemaVersion": 2,
  "restartable": true,
  "workflowStatusListenerEnabled": false,
  "timeoutPolicy": "TIME_OUT_WF",
  "timeoutSeconds": 60,
  "variables": {},
  "inputTemplate": {},
  "enforceSchema": true,
  "metadata": {}
}
```

## Develop the workers:

- The actual workers `workers_collection.py`, **get_name** and **get_id**:
```python
from conductor.client.worker.worker_task import worker_task


@worker_task(task_definition_name='get_name')
def get_name(name: str) -> str:
    return f'Hello {name}'

@worker_task(task_definition_name='get_id')
def get_id(id: str) -> str:
    return f'id: {id}'

```

- The workers wrapper `helloworld.py`:

```python
from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.workflow.executor.workflow_executor import WorkflowExecutor

# Import the simple workers defined
from  workers_collection import get_name,get_id


def main():
    # The workers are connected to this endpoint for MicroTx Workflows:  http://<localhost>/workflow-server/api
    api_config = Configuration()

    workflow_executor = WorkflowExecutor(configuration=api_config)

    # Starting the polling
    task_handler = TaskHandler(configuration=api_config)
    task_handler.start_processes()


if __name__ == '__main__':
    main()
```

### Execution
- To start the worker:
```sh
python helloworld.py
```
You should see, if it works:

```sh
[oracle@microtx-workflowengine:~/custom_client]$ python helloworld.py 
2026-02-12 14:35:26,548 [2409475] conductor.client.automator.task_handler INFO     TaskHandler initialized
2026-02-12 14:35:26,548 [2409475] conductor.client.automator.task_handler INFO     Starting worker processes...
task runner process Process-2 started
2026-02-12 14:35:26,551 [2409475] conductor.client.automator.task_runner INFO     Conductor Worker[name=get_name, pid=2409477, status=active, poll_interval=100ms, thread_count=1, poll_timeout=100ms, lease_extend=false, register_task_def=false]
task runner process Process-3 started
2026-02-12 14:35:26,555 [2409475] conductor.client.automator.task_handler INFO     Started 2 TaskRunner process(es)
2026-02-12 14:35:26,556 [2409475] conductor.client.automator.task_runner INFO     Conductor Worker[name=get_id, pid=2409478, status=active, poll_interval=100ms, thread_count=1, poll_timeout=100ms, lease_extend=false, register_task_def=false]
2026-02-12 14:35:26,556 [2409475] conductor.client.automator.task_handler INFO     Started all processes
```

- To start the workflow, go in **Workbench**, look for **Workflow name**: `simple_worker`

<p align="center">
  <img src="images/start_workflow.png" alt="similarity" width="600">
</p>

set the input, and start.

- to show the trace:
<p align="center">
  <img src="images/workflow_execution.png" alt="similarity" width="600">
</p>

### Collaterals
- If you want to check if any tasks are in the queue:

```sh
curl -X GET http://10.107.38.138/workflow-server/api/tasks/poll/batch/get_name
```
- If you want take a look to the list of REST API:
```sh
http://10.107.38.138/workflow-server/swagger-ui/index.html#/metadata-resource/getAll
```


## Disclaimer
*The views expressed in this paper are my own and do not necessarily reflect the views of Oracle.*