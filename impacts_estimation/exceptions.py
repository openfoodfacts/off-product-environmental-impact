""" Exceptions used by the impact estimation program """


class RecipeCreationError(Exception):
    pass


class SolverTimeoutError(Exception):
    pass


class NoKnownIngredientsError(Exception):
    pass


class NoCharacterizedIngredientsError(Exception):
    pass
