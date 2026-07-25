from .context import UserContext

class BaseService:
    """
    Base class for all Domain Services.
    Enforces that every service instance operates within a specific UserContext.
    """
    def __init__(self, context: UserContext):
        if not context:
            raise ValueError("Service requires a valid UserContext.")
        self.context = context

    @property
    def user_id(self):
        return self.context.user_id

    @property
    def chain_id(self):
        return self.context.chain_id

    @property
    def store_id(self):
        return self.context.store_id
