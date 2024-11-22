
class NotFoundException(Exception):
    def __init__(self, target):
        self.msg = target + " is not found."

    def __str__(self):
        return self.msg
    
class RoutineCheckError(Exception):
    def __init__(self):
        self.msg = "Routine check failed."

    def __str__(self):
        return self.msg