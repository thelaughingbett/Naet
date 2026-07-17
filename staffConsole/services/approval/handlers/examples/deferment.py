
from staffConsole.services.approval import AbstractApprovalHandler
from base.models import Deferment


class DefermentApprovalHandler(AbstractApprovalHandler):

    def get_pending(self):
        return Deferment.objects.filter(status='pending').select_related('student__user')

    def approve(self, instance, approved_by, **kwargs):
        instance.status = 'approved'
        instance.approved_by = approved_by
        instance.save()
        instance.student.deferred = True
        instance.student.save()
        return instance

    def reject(self, instance, rejected_by, reason, **kwargs):
        instance.status = 'rejected'
        instance.rejection_reason = reason
        instance.save()
        return instance

    def to_card_context(self, instance):
        return {
            'student_name': instance.student.user.full_name,
            'reg_no':       instance.student.registration_number,
            'reason':       instance.get_reason_display(),
            'from_session': str(instance.session_deferred),
            'to_session':   str(instance.session_returning) if instance.session_returning else 'TBD',
        }
