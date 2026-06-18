# base/modules/exam_timetable/generators/greedy.py

from base.modules.timetabling.exam_timetable.base import (
    AbstractExamTimetableGenerator,
    ExamConstraints,
    ExamPlan,
    ExamSlot,
)


class GreedyExamGenerator(AbstractExamTimetableGenerator):
    """
    Slot-by-slot greedy placement — the default exam timetable generator.

    Iterates curriculum entries in order. For each entry walks date × slot
    until a free (venue, invigilator) pair is found. First-fit — not globally
    optimal but fast and deterministic. Good for small-to-medium cohorts.
    """

    generator_name = 'greedy'

    def generate(self, constraints: ExamConstraints) -> ExamPlan:
        plan = ExamPlan(metadata={'generator': self.generator_name})

        venue_busy = {}
        invig_busy = {}
        class_busy = {}
        student_busy = {}

        for entry in constraints.curriculum_entries:
            placed = False
            enrolled = entry['enrolled_student_ids']

            for date in constraints.exam_dates:
                if placed:
                    break
                for slot in constraints.slots:
                    if class_busy.get((entry['id'], date, slot)):
                        continue
                    if any(student_busy.get((sid, date, slot)) for sid in enrolled):
                        continue

                    venue = self._free_venue(
                        constraints.venues, venue_busy, date, slot)
                    if not venue:
                        continue

                    invigilator = self._free_invigilator(
                        preferred=entry['professor_ids'],
                        all_invigilators=constraints.invigilators,
                        invig_busy=invig_busy,
                        date=date,
                        slot=slot,
                    )
                    if not invigilator:
                        continue

                    class_busy[(entry['id'], date, slot)] = True
                    venue_busy[(venue['record_id'], date, slot)] = True
                    invig_busy[(invigilator['record_id'], date, slot)] = True
                    for sid in enrolled:
                        student_busy[(sid, date, slot)] = True

                    plan.slots.append(ExamSlot(
                        curriculum_id=entry['id'],
                        date=date,
                        time_slot=slot,
                        venue_id=venue['record_id'],
                        invigilator_id=invigilator['record_id'],
                        exam_type=constraints.exam_type,
                    ))
                    placed = True
                    break

            if not placed:
                plan.warnings.append(
                    f"Could not place {constraints.exam_type} exam for "
                    f"{entry['course_code']} ({entry['class_name']}) — "
                    f"no available slot found."
                )

        return plan

    def _free_venue(self, venues, venue_busy, date, slot):
        for v in venues:
            if not venue_busy.get((v['record_id'], date, slot)):
                return v
        return None

    def _free_invigilator(self, preferred, all_invigilators, invig_busy, date, slot):
        all_by_id = {i['record_id']: i for i in all_invigilators}
        for pid in preferred:
            inv = all_by_id.get(pid)
            if inv and not invig_busy.get((pid, date, slot)):
                return inv
        for inv in all_invigilators:
            if not invig_busy.get((inv['record_id'], date, slot)):
                return inv
        return None
