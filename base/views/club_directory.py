from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from base.models import Club, ClubMembership
from .base import StudentProfileRequiredMixin, StudentContextMixin


class ClubDirectoryView(
    LoginRequiredMixin,
    StudentProfileRequiredMixin,
    StudentContextMixin,
    View
):
    def get(self, request):
        student = self.get_student(request)

        clubs = Club.objects.exclude(
            status='dissolved'
        ).prefetch_related(
            'leadership_positions__member__student__user',
            'club_patrons__staff',
        )

        my_membership_status = {}
        if student:
            my_membership_status = {
                str(m.club_id): m.status
                for m in ClubMembership.objects.filter(student=student)
            }

        clubs_data = []
        for club in clubs:
            leaders = [
                {'name': p.staff.full_name, 'role': p.get_role_display()}
                for p in club.current_patrons
            ] + [
                {
                    'name': pos.member.student.user.full_name,
                    'role': pos.get_position_display(),
                }
                for pos in club.current_leadership
            ]

            clubs_data.append({
                'id': str(club.record_id),
                'name': club.name,
                'code': club.code,
                'category': club.category,
                'category_label': club.get_category_display(),
                'description': club.description or "No description provided yet.",
                'members': club.active_member_count,
                'capacity': club.membership_capacity,
                'is_full': club.is_full,
                'status': club.status,
                'status_label': club.get_status_display(),
                'annual_dues': club.annual_dues,
                'leaders': leaders,
                'events': [],  # no ClubEvent model yet
                'my_status': my_membership_status.get(str(club.record_id)),
            })

        context = {
            'clubs_data': clubs_data,
            'student': student,
            'active_club_count': clubs.filter(status='active').count(),
        }
        return render(request, 'base/clubs/student_club_directory.html', context)

    def post(self, request):
        """
        Submit (or resubmit) a join request for a club, using the real
        ClubMembership lifecycle: new applications start 'pending' and
        need approve()/reject() by a club exec — this view only ever
        creates or resets to 'pending', it never sets 'active' directly.
        """
        student = self.get_student(request)
        if not student:
            return JsonResponse({'success': False, 'message': 'No student profile.'}, status=403)

        club_id = request.POST.get('club_id')
        club = Club.objects.filter(record_id=club_id).first()
        if not club:
            return JsonResponse({'success': False, 'message': 'Club not found.'}, status=404)

        if club.status != 'active':
            return JsonResponse({
                'success': False,
                'message': 'This club is not currently accepting members.',
            }, status=400)

        if club.is_full:
            return JsonResponse({
                'success': False,
                'message': 'This club has reached its membership capacity.',
            }, status=400)

        existing = ClubMembership.objects.filter(
            student=student, club=club).first()

        if existing:
            if existing.status == 'active':
                return JsonResponse({'success': False, 'message': 'You are already a member of this club.'}, status=400)
            if existing.status == 'pending':
                return JsonResponse({'success': False, 'message': 'You already have a pending request for this club.'}, status=400)
            if existing.status == 'suspended':
                return JsonResponse({'success': False, 'message': 'Your membership is suspended — contact the club patron.'}, status=400)
            # 'inactive', 'alumni', 'withdrawn' — allow reapplying by
            # resetting to pending. Clear the fields clean() ties to a
            # closed membership so a stale rejection/date_left doesn't
            # linger on what is now a fresh application.
            existing.status = 'pending'
            existing.date_left = None
            existing.rejection_reason = ''
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.motivation = request.POST.get('motivation', '')
            existing.full_clean()
            existing.save()
        else:
            membership = ClubMembership(
                student=student,
                club=club,
                status='pending',
                motivation=request.POST.get('motivation', ''),
            )
            membership.full_clean()
            membership.save()

        return JsonResponse({'success': True, 'message': f'Join request sent to {club.name}.'})
