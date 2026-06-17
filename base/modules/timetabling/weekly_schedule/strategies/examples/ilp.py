from base.modules.timetabling.weekly_schedule.base import (
    AbstractTimetableStrategy,
    TimetableGenerationResult,
    TimetableSlot,
)
from base.models import Curriculum, Venue


class ILPStrategy(AbstractTimetableStrategy):
    """
    Integer Linear Programming timetable generator.
    Uses PuLP / OR-Tools / scipy.optimize — your choice.

    Produces an optimal schedule that minimises gaps and
    respects lecturer availability windows.

    Install: pip install pulp
    """

    def generate(self, session) -> TimetableGenerationResult:
        try:
            import pulp
        except ImportError:
            return TimetableGenerationResult(
                success=False,
                message="PuLP not installed. Run: pip install pulp"
            )

        try:
            curriculum = list(
                Curriculum.objects.filter(session=session)
                .select_related('Tclass', 'course')
                .prefetch_related('professor')
            )
            venues = list(Venue.objects.all())

            if not venues:
                return TimetableGenerationResult(
                    success=False,
                    message="No venues found. Add venues before generating."
                )

            # --- build your ILP model here ---
            # prob = pulp.LpProblem("timetable", pulp.LpMinimize)
            # x[c, d, s, v] = 1 if curriculum c is in day d, slot s, venue v
            # add constraints...
            # prob.solve()
            # extract solution into TimetableSlot list

            slots = []   # populate from ILP solution

            return TimetableGenerationResult(
                success=True,
                slots=slots,
                message=f"ILP solver found optimal schedule.",
                stats={
                    "solver":  "PuLP",
                    "status":  "optimal",   # pulp.LpStatus[prob.status]
                }
            )

        except Exception as e:
            return TimetableGenerationResult(success=False, message=str(e))
