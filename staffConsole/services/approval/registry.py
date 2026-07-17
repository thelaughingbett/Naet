class ApprovalRegistry:
    """
    Maps an approval_type string to the logic that knows how to
    approve/reject that kind of request, and how to notify on outcome.

    Register in AppConfig.ready():
        approval_registry.register('deferment', DefermentApprovalHandler())
        approval_registry.register('enrollment', EnrollmentApprovalHandler())
    """
    _handlers = {}

    @classmethod
    def register(cls, approval_type, handler):
        cls._handlers[approval_type] = handler

    @classmethod
    def get(cls, approval_type):
        return cls._handlers.get(approval_type)


approval_registry = ApprovalRegistry()
