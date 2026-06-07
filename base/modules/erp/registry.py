from typing import Dict, List
from .tasks.base import AbstractERPTask


class ERPRegistry:
    """
    Maps event strings to their ERP task handlers.

    Multiple tasks can handle the same event — all will be called.

    Register in AppConfig.ready():
        erp_registry.register(PaymentERPTask())
        erp_registry.register(EnrollmentERPTask())

    """

    _tasks: Dict[str, List[AbstractERPTask]] = {}

    @classmethod
    def register(cls, task: AbstractERPTask):
        events = (
            [task.event]
            if isinstance(task.event, str)
            else task.event
        )
        for event in events:
            if event:
                cls._tasks.setdefault(event, []).append(task)

    @classmethod
    def get(cls, event: str) -> List[AbstractERPTask]:
        return cls._tasks.get(event, [])

    @classmethod
    def all(cls) -> Dict[str, List[AbstractERPTask]]:
        return dict(cls._tasks)


erp_registry = ERPRegistry()
