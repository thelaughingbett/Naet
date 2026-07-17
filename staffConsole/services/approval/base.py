from abc import ABC, abstractmethod


class AbstractApprovalHandler(ABC):
    """
    One handler per approval type (deferment, enrollment override, etc.)
    Knows how to render a summary card, approve, and reject.
    """

    @abstractmethod
    def get_pending(self):
        """Return queryset of pending instances for this approval type."""
        raise NotImplementedError

    @abstractmethod
    def approve(self, instance, approved_by, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def reject(self, instance, rejected_by, reason, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def to_card_context(self, instance) -> dict:
        """Return dict for rendering the approval card in templates."""
        raise NotImplementedError
