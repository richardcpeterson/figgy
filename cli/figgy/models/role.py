
class Role:

    def __init__(self, role: str, full_name: str = None):
        self.role = role
        self.full_name = full_name

    def __str__(self):
        return self.role

    def __eq__(self, other):
        return self.role == other.role