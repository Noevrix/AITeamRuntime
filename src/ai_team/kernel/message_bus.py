from ai_team.protocol.message import Message


class MessageBus:
    def __init__(self, db, registry, events):
        self.db, self.registry, self.events = db, registry, events

    def send(self, message: Message):
        for agent in (message.from_agent, message.to_agent):
            if agent not in {"user", "kernel"}:
                self.registry.get(agent)
        task = self.db.get("tasks", message.task_id)
        if not task or task["project_id"] != message.project_id:
            raise ValueError("message task/project mismatch")
        self.db.put("messages", message)
        self.events.emit(message.project_id, "MESSAGE_SENT", message.task_id, message_id=message.id, message_type=message.type)
