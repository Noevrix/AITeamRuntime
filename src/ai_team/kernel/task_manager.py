from ai_team.protocol.task import Task, TaskStatus as S, now

ALLOWED = {
    S.PENDING: {S.ASSIGNED, S.CANCELLED, S.ESCALATED},
    S.ASSIGNED: {S.RUNNING, S.CANCELLED, S.FAILED, S.ESCALATED},
    S.RUNNING: {S.REVIEW, S.COMPLETED, S.FAILED, S.CANCELLED, S.ESCALATED},
    S.REVIEW: {S.COMPLETED, S.CHANGES_REQUESTED, S.FAILED, S.CANCELLED, S.ESCALATED},
    S.CHANGES_REQUESTED: {S.RUNNING, S.COMPLETED, S.FAILED, S.CANCELLED, S.ESCALATED},
}


class TaskManager:
    def __init__(self, db, events):
        self.db, self.events = db, events

    def create(self, task):
        if self.db.get("tasks", task.id):
            raise ValueError("duplicate task")
        self.db.put("tasks", task)
        self.events.emit(task.project_id, "TASK_CREATED", task.id)
        return task

    def get(self, task_id):
        data = self.db.get("tasks", task_id)
        if data is None:
            raise KeyError(task_id)
        return Task.model_validate(data)

    def transition(self, task_id, status):
        task = self.get(task_id)
        if status not in ALLOWED.get(task.status, set()):
            raise ValueError(f"invalid transition: {task.status} -> {status}")
        previous = task.status
        task.status, task.updated_at = status, now()
        self.db.put("tasks", task)
        self.events.emit(task.project_id, "TASK_STATE", task.id, previous=previous, status=status)
        return task
