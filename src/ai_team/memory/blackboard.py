from ai_team.protocol.task import uid


class Blackboard:
    def __init__(self, db):
        self.db = db

    def decide(self, project_id, content):
        value = {"id": uid(), "project_id": project_id, "content": content}
        self.db.put("decisions", value)
        return value

    def snapshot(self, project_id):
        project = self.db.get("projects", project_id)
        if project is None:
            raise KeyError(project_id)
        return {"project": project, **{name: self.db.list(name, project_id) for name in ("decisions", "tasks", "artifacts")}}
