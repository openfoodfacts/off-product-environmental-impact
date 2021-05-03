""" Settings used by the impact estimation program. """

# Proportion from which the ingredients don't have to be ordered by decreasing proportion in the ingredient list
DECREASING_PROPORTION_ORDER_LIMIT = 0.02  # From EU regulations

MINIMUM_TOTAL_MASS_FOR_UNBALANCED_RECIPES = 0.5

# Ratio of uncharacterized ingredients (no nutritional or impact data) in the product from which the result
#  should contain a warning
UNCHARACTERIZED_INGREDIENTS_RATIO_WARNING_THRESHOLD = 0.25

# Mass proportion of uncharacterized ingredients (no nutritional or impact data) in the product from which the result
#  should contain a warning
UNCHARACTERIZED_INGREDIENTS_MASS_WARNING_THRESHOLD = 0.10

# Impact relative interquartile from which the result should contain a warning
IMPACT_RELATIVE_INTERQUARTILE_WARNING_THRESHOLD = 0.25

# 0: No output, 1: ImpactEstimator output, 2: + RandomCompositionCreator outputs, 3: + Solver output
VERBOSITY = 0

# Duration of the solver timeout in seconds
SOLVER_TIMEOUT = 120

# Maximum consecutive composition creation error before to raise CompositionCreationError
MAX_CONSECUTIVE_RECIPE_CREATION_ERROR = 3

# Maximum consecutive composition creation error before to raise NoCharacterizedIngredientsError
MAX_CONSECUTIVE_NULL_IMPACT_CHARACTERIZED_INGREDIENTS_MASS = 3

# Step of the total mass confidence score distribution estimation in g
TOTAL_MASS_DISTRIBUTION_STEP = 1

# Only used to ensure compatibility with old OFF database format for calculation on old database dumps.
# OFF_INGREDIENTS_FORMAT = 'Flat with rank'
OFF_INGREDIENTS_FORMAT = 'Ingredient tree'
