""" Environmental impact estimation for Open Food Facts products """

from impacts_estimation.impact_estimation import estimate_impacts, estimate_impacts_safe
from impacts_estimation.exceptions import RecipeCreationError, NoKnownIngredientsError, \
    NoCharacterizedIngredientsError, SolverTimeoutError
