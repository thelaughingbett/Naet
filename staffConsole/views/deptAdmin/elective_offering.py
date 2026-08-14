"""
Elective Offerings — HOD-facing views.

Two distinct workflows, deliberately kept separate rather than one flat
"Add Elective" form (which the mockup implied but the relational model
can't actually support as a single insert):

  1. PROPOSING a new elective — creating a Syllabus row (course x programme,
     state=PROPOSED). Committee-level, infrequent, requires approval before
     it can ever be scheduled.
  2. OFFERING an already-approved elective this term — creating a
     Curriculum row (syllabus x Tclass x session, capacity). HOD-level,
     every session, only possible once step 1 has reached an
     Syllabus.SCHEDULABLE_STATE.

Curriculum.clean() already enforces this ordering server-side (it raises
ValidationError if syllabus.state isn't schedulable) — these views just
make sure the UI doesn't offer an action that would fail validation anyway.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from base.models import Curriculum, LecturerAssignment, Session, Syllabus, Tclass


# ---------------------------------------------------------------------------
# Department scoping
# ---------------------------------------------------------------------------

def get_hod_department(user):
    """
    An HOD is a Lecturer with role='hod' (see Lecturer.is_hod). Views below
    scope every query to this department — an HOD should never see or edit
    another department's offerings, regardless of what a query param claims.
    """
    lecturer = getattr(user, "lecturer_profile", None)
    if lecturer is None or not lecturer.is_hod:
        raise PermissionDenied(
            "Only a Head of Department can manage elective offerings.")
    return lecturer.department


class HODDepartmentScopedMixin(LoginRequiredMixin):
    """Attaches self.department (the requesting HOD's own department) to every view below."""

    def dispatch(self, request, *args, **kwargs):
        self.department = get_hod_department(request.user)
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Status computation — kept out of the models, since "open/full/pending/
# closed" is a reporting concept specific to this screen, not a property of
# Curriculum in general (a Curriculum entry for a Core course has no
# meaningful "elective offering status").
# ---------------------------------------------------------------------------

OFFERING_STATUS_LABELS = {
    "pending": "Pending",
    "open": "Open",
    "full": "Full",
    "closed": "Closed",
}


def compute_offering_status(curriculum, enrolled_count, has_confirmed_instructor, today=None):
    today = today or timezone.now().date()

    if curriculum.syllabus.state not in Syllabus.SCHEDULABLE_STATES:
        # Shouldn't normally exist as a Curriculum row at all (clean()
        # blocks it) — defensive fallback in case of legacy/migrated data.
        return "pending"
    if not has_confirmed_instructor:
        return "pending"
    if curriculum.session.end_date and curriculum.session.end_date < today:
        return "closed"
    if enrolled_count >= curriculum.capacity:
        return "full"
    return "open"


def annotate_offerings(queryset):
    """Attaches enrolled_count and has_confirmed_instructor via SQL aggregation."""
    return queryset.annotate(
        enrolled_count=Count(
            "enrollment_records",
            filter=Q(enrollment_records__status__in=["approved", "completed"]),
            distinct=True,
        ),
        confirmed_instructor_count=Count(
            "lecturer_assignments",
            filter=Q(
                lecturer_assignments__is_primary=True,
                lecturer_assignments__status__in=["Assigned", "Confirmed"],
            ),
            distinct=True,
        ),
    )


def attach_computed_status(offerings):
    """Python-side pass to attach .offering_status to each row after fetch — small admin-scale
    row counts (tens per department per session), so this is clearer than a giant SQL CASE/WHEN."""
    today = timezone.now().date()
    for offering in offerings:
        offering.offering_status = compute_offering_status(
            offering, offering.enrolled_count, offering.confirmed_instructor_count > 0, today
        )
    return offerings


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class ElectiveOfferingListView(HODDepartmentScopedMixin, ListView):
    """
    Curriculum entries whose syllabus.course.course_type is Elective, Common
    Unit, or Practical (the mockup's E/CC/P filter), scoped to this HOD's
    department, with capacity-derived status plus the syllabus's own
    approval state surfaced as a separate column.
    """

    template_name = "curriculum/elective_offerings/list.html"
    context_object_name = "offerings"
    paginate_by = 10

    ELECTIVE_COURSE_TYPES = ("E", "CC", "P")

    def get_base_queryset(self):
        qs = Curriculum.objects.select_related(
            "syllabus__course", "syllabus__programme", "Tclass", "session"
        ).filter(
            syllabus__programme__department=self.department,
            syllabus__course__course_type__in=self.ELECTIVE_COURSE_TYPES,
        )
        session_id = self.request.GET.get("session")
        if session_id and session_id != "all":
            qs = qs.filter(session_id=session_id)
        return annotate_offerings(qs)

    def get_queryset(self):
        qs = self.get_base_queryset()

        course_type = self.request.GET.get("type")
        if course_type and course_type != "all":
            qs = qs.filter(syllabus__course__course_type=course_type)

        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(syllabus__course__course_code__icontains=search)
                | Q(syllabus__course__course_name__icontains=search)
                | Q(lecturer_assignments__lecturer__user__first_name__icontains=search)
                | Q(lecturer_assignments__lecturer__user__last_name__icontains=search)
            ).distinct()

        offerings = attach_computed_status(list(qs))

        status = self.request.GET.get("status")
        if status and status != "all":
            offerings = [o for o in offerings if o.offering_status == status]

        return offerings

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Stats always reflect the department+session scope, not the
        # current filters — matches the mockup, where stat cards don't
        # move when you type into the search box.
        all_offerings = attach_computed_status(list(self.get_base_queryset()))
        context["stats"] = {
            status: sum(
                1 for o in all_offerings if o.offering_status == status)
            for status in OFFERING_STATUS_LABELS
        }
        context["total_count"] = len(all_offerings)
        context["sessions"] = Session.objects.order_by("-start_date")
        context["department"] = self.department
        return context


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class ElectiveOfferingDetailView(HODDepartmentScopedMixin, DetailView):
    template_name = "curriculum/elective_offerings/detail.html"
    context_object_name = "offering"

    def get_queryset(self):
        return annotate_offerings(
            Curriculum.objects.select_related(
                "syllabus__course", "syllabus__programme", "Tclass", "session"
            ).prefetch_related("lecturer_assignments__lecturer__user")
            .filter(syllabus__programme__department=self.department)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offering = context["offering"]
        offering.offering_status = compute_offering_status(
            offering, offering.enrolled_count, offering.confirmed_instructor_count > 0
        )
        context["prerequisites"] = offering.syllabus.course.prerequisites.all()
        context["instructors"] = offering.lecturer_assignments.select_related(
            "lecturer__user")
        return context


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class ElectiveOfferingForm(forms.ModelForm):
    """
    Creates/updates the Curriculum row — i.e. "offer this already-approved
    elective to this class, this session". `syllabus` is deliberately
    restricted to entries already in a SCHEDULABLE_STATE for this
    department, so the form can't even present an option that
    Curriculum.clean() would reject.
    """

    class Meta:
        model = Curriculum
        fields = ["syllabus", "Tclass", "session",
                  "capacity", "weekly_allocated_slots"]

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)
        if department is not None:
            self.fields["syllabus"].queryset = Syllabus.objects.filter(
                programme__department=department,
                state__in=Syllabus.SCHEDULABLE_STATES,
            ).select_related("course", "programme")
            self.fields["Tclass"].queryset = Tclass.objects.filter(
                programme__department=department
            )


class AssignInstructorForm(forms.ModelForm):
    class Meta:
        model = LecturerAssignment
        fields = ["lecturer", "is_primary", "allocated_workload_hours"]


class ProposeSyllabusForm(forms.ModelForm):
    """
    Step 1 of the two-step workflow — proposes a new course x programme
    pairing. Always created as PROPOSED regardless of what's submitted;
    approval is a separate, higher-privilege action (see approve_syllabus
    below), not something this form can grant itself.
    """

    class Meta:
        model = Syllabus
        fields = ["programme", "course", "notes"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.state = Syllabus.State.PROPOSED
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Create / Update (offering an already-approved elective)
# ---------------------------------------------------------------------------

class ElectiveOfferingCreateView(HODDepartmentScopedMixin, CreateView):
    model = Curriculum
    form_class = ElectiveOfferingForm
    template_name = "curriculum/elective_offerings/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["department"] = self.department
        return kwargs

    def form_valid(self, form):
        try:
            self.object = form.save(commit=False)
            # surfaces Curriculum.clean()'s syllabus-state/programme checks
            self.object.full_clean()
            self.object.save()
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Offered {self.object.syllabus.course.course_code} to "
            f"{self.object.Tclass} for {self.object.session}.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("elective-offering-detail", kwargs={"pk": self.object.pk})


class ElectiveOfferingUpdateView(HODDepartmentScopedMixin, UpdateView):
    """Edit capacity/session/class for an existing offering — the mockup's 'Edit' button."""

    model = Curriculum
    form_class = ElectiveOfferingForm
    template_name = "curriculum/elective_offerings/form.html"

    def get_queryset(self):
        return Curriculum.objects.filter(syllabus__programme__department=self.department)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["department"] = self.department
        return kwargs

    def get_success_url(self):
        return reverse("elective-offering-detail", kwargs={"pk": self.object.pk})


# ---------------------------------------------------------------------------
# Propose (step 1) and manage instructor assignment
# ---------------------------------------------------------------------------

class ProposeSyllabusView(HODDepartmentScopedMixin, CreateView):
    """
    'Propose a new elective' — separate entry point from offering one,
    since a brand-new Syllabus row starts PROPOSED and can't be scheduled
    (Curriculum.clean() blocks it) until someone with approval authority
    moves it to Approved/Adjunct.
    """

    model = Syllabus
    form_class = ProposeSyllabusForm
    template_name = "curriculum/elective_offerings/propose.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {**kwargs.get("initial", {})}
        return kwargs

    def form_valid(self, form):
        form.instance.proposed_by = self.request.user
        response = super().form_valid(form)
        messages.info(
            self.request,
            f"{self.object.course} proposed for {self.object.programme} — "
            f"awaiting approval before it can be offered.",
        )
        return response

    def get_success_url(self):
        return reverse("elective-offering-list")


def assign_instructor(request, curriculum_pk):
    """
    Function view (not a class) since it's a single focused action off the
    detail page's 'Manage' button, not its own list/detail/CRUD surface.
    """
    department = get_hod_department(request.user)
    curriculum = get_object_or_404(
        Curriculum, pk=curriculum_pk, syllabus__programme__department=department
    )

    if request.method == "POST":
        form = AssignInstructorForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.curriculum = curriculum
            try:
                assignment.full_clean()  # enforces the 40hr/week + one-primary-per-slot rules
                assignment.save()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request, f"{assignment.lecturer} assigned to {curriculum}.")
                return redirect("elective-offering-detail", pk=curriculum.pk)
    else:
        form = AssignInstructorForm()

    from django.shortcuts import render
    return render(
        request,
        "curriculum/elective_offerings/assign_instructor.html",
        {"form": form, "curriculum": curriculum},
    )
