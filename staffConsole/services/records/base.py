from base.models import StudentFeeAccount, Result


class StudentRecordService:
    @staticmethod
    def get_full_record(student):
        return {
            'student':     student,
            'fee_account': StudentFeeAccount.objects.filter(student=student).select_related('fee_structure').first(),
            'deferments':  student.deferments.order_by('-created_at'),
            'enrollments': student.enrollment_records.select_related('curriculum__course'),
            'results':     Result.objects.filter(student=student).select_related('curricula__course'),
        }
