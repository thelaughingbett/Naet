from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from base.models import ClubMembership, ClubLeadershipPosition, ClubEvent
from .base import StudentProfileRequiredMixin, StudentContextMixin


class MyMembershipsView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    """
    Was previously misnamed ClubDirectoryView in an earlier draft —
    renamed since it renders a different template (student_my_clubs.html)
    with entirely different data (a student's own memberships, not the
    full club catalog). Update urls.py if it still points at the old name.
    """

    # A withdrawn/rejected membership shouldn't linger on "My Memberships"
    # once the student has explicitly left or been declined.
    VISIBLE_STATUSES = ['pending', 'active', 'inactive', 'suspended', 'alumni']

    def get(self, request):
        student = self.get_student(request)
        memberships_data = []

        if student:
            memberships = ClubMembership.objects.filter(
                student=student,
                status__in=self.VISIBLE_STATUSES,
            ).select_related('club').order_by('-date_joined')

            membership_ids = [m.record_id for m in memberships]

            # Active leadership positions this student holds, fetched in
            # one query rather than N+1 per membership card.
            leadership_by_membership = {
                lp.member_id: lp
                for lp in ClubLeadershipPosition.objects.filter(
                    member_id__in=membership_ids, is_active=True
                )
            }

            now = timezone.now()
            for membership in memberships:
                club = membership.club
                role_type, role_label = self._resolve_role(
                    leadership_by_membership.get(membership.record_id)
                )

                upcoming_events = ClubEvent.objects.filter(
                    club=club,
                    approval_status='approved',
                    start_time__gte=now,
                ).order_by('start_time')[:10]

                memberships_data.append({
                    'membership_id': str(membership.record_id),
                    'club_id': str(club.record_id),
                    'club_name': club.name,
                    'category': club.category,
                    'category_label': club.get_category_display(),
                    'description': club.description or "No description provided yet.",
                    'member_count': club.active_member_count,
                    'status': membership.status,
                    'status_label': membership.get_status_display(),
                    'role_type': role_type,
                    'role_label': role_label,
                    'date_joined': membership.date_joined.strftime('%Y-%m-%d'),
                    'leaders': self._club_leaders(club),
                    'events': [
                        {
                            'title': e.title,
                            'date': e.start_time.strftime('%Y-%m-%d'),
                            'time': e.start_time.strftime('%I:%M %p'),
                        }
                        for e in upcoming_events
                    ],
                })

        context = {
            'memberships_data': memberships_data,
            'student': student,
        }
        return render(request, 'base/clubs/student_my_clubs.html', context)

    def post(self, request):
        """
        Self-service leave. Also closes out any active leadership term
        this membership holds — ClubLeadershipPosition.clean() requires
        an active member, so a withdrawn membership can't be left
        holding a live position.
        """
        student = self.get_student(request)
        if not student:
            return JsonResponse({'success': False, 'message': 'No student profile.'}, status=403)

        membership_id = request.POST.get('membership_id')
        membership = ClubMembership.objects.filter(
            record_id=membership_id, student=student
        ).select_related('club').first()

        if not membership:
            return JsonResponse({'success': False, 'message': 'Membership not found.'}, status=404)

        if membership.status not in ('active', 'pending', 'inactive'):
            return JsonResponse({
                'success': False,
                'message': f"Can't leave a membership in '{membership.get_status_display()}' status.",
            }, status=400)

        club_name = membership.club.name

        ClubLeadershipPosition.objects.filter(
            member=membership, is_active=True
        ).update(is_active=False, end_date=timezone.now().date())

        membership.status = 'withdrawn'
        try:
            membership.full_clean()
            membership.save()
        except ValidationError as e:
            messages = []
            for _, errs in getattr(e, 'message_dict', {'__all__': e.messages}).items():
                messages.extend(errs)
            return JsonResponse({'success': False, 'message': ' '.join(messages)}, status=400)

        return JsonResponse({'success': True, 'message': f'You have left {club_name}.'})

    @staticmethod
    def _resolve_role(position):
        """
        Maps an active ClubLeadershipPosition (or None) to a
        (role_type, role_label) pair for the card's badge:
        chairperson -> 'head', other admin-granting positions -> 'leader',
        committee_member or no position at all -> 'member'.
        """
        if position is None:
            return 'member', 'Member'
        if position.position == 'chairperson':
            return 'head', position.get_position_display()
        if position.position in ClubLeadershipPosition.ADMIN_POSITIONS:
            return 'leader', position.get_position_display()
        return 'member', position.get_position_display()  # committee_member

    @staticmethod
    def _club_leaders(club):
        return [
            {'name': p.staff.full_name, 'role': p.get_role_display()}
            for p in club.current_patrons
        ] + [
            {
                'name': pos.member.student.user.full_name,
                'role': pos.get_position_display(),
            }
            for pos in club.current_leadership
        ]
