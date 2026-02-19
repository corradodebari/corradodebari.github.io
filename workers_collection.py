from conductor.client.worker.worker_task import worker_task


@worker_task(task_definition_name='get_name')
def get_name(name: str) -> str:
    return f'Hello {name}'

@worker_task(task_definition_name='get_id')
def get_id(id: str) -> str:
    return f'id: {id}