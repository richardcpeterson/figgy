from abc import ABC

from commands.command_context import CommandContext
from commands.iam_context import IAMContext
from commands.types.command import Command


class IAMCommand(Command, ABC):
    """
    Config command class from which all other config command classes inherit.
    """

    def __init__(self, command_type: frozenset, context: IAMContext):
        super().__init__(command_type, context.colors_enabled, CommandContext(context.run_env, context.resource))
        self.role = context.role
