from ai_team.protocol.event import Event


class EventBus:
    def __init__(self, db):
        self.db = db

    def emit(self, project_id, kind, task_id=None, **metadata):
        event = Event(project_id=project_id, task_id=task_id, type=kind, metadata=metadata)
        self.db.put("events", event)
        return event
