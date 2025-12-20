"""Invalid Project Exception"""


class InvalidProject(Exception):
    """Raised when project data is invalid."""
    
    def __init__(self, project_id: str = None, message: str = None):
        self.project_id = project_id
        self.message = message or f"Invalid project: {project_id}" if project_id else "Invalid project data"
        super().__init__(self.message)
