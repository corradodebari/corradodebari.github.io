from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from conductor.client.workflow.executor.workflow_executor import WorkflowExecutor

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