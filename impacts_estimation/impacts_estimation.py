""" Environmental impact estimation for Open Food Facts products  """

import warnings
import time
from random import uniform, shuffle, choice
from statistics import mean
import copy
import math

# ### FOR DEBUG PURPOSE ONLY ###
# import matplotlib.pyplot as plt
# import seaborn as sns
#
# sns.set()
# ##############################

import statsmodels.stats.api as sms
import numpy as np
from sklearn.neighbors import KernelDensity
from pyscipopt import Model

from impacts_estimation.utils import natural_bounds, nutritional_error_margin, \
    clear_ingredient_graph, define_subingredients_percentage_type, find_ingredients_graph_leaves, \
    flat_ingredients_list_BFS, individualize_ingredients, original_id, nutriments_from_recipe, \
    remove_percentage_from_product, confidence_score, UnknownIngredientsRemover
from impacts_estimation.vars import NUTRIMENTS_CATEGORIES, QUALITY_DATA_WARNINGS, \
    TOP_LEVEL_NUTRIMENTS_CATEGORIES, MAX_ASH_CONTENT, FERMENTATION_AGENTS, FERMENTED_FOOD_CATEGORIES, \
    HIGH_WATER_LOSS_CATEGORIES, IMPACT_MASS_UNIT, AGRIBALYSE_IMPACT_UNITS, RESULTS_WARNINGS_NOT_RELIABLE
from settings import VERBOSITY, IMPACT_RELATIVE_INTERQUARTILE_WARNING_THRESHOLD, \
    UNCHARACTERIZED_INGREDIENTS_MASS_WARNING_THRESHOLD, \
    UNCHARACTERIZED_INGREDIENTS_RATIO_WARNING_THRESHOLD, MAX_CONSECUTIVE_RECIPE_CREATION_ERROR, \
    DECREASING_PROPORTION_ORDER_LIMIT, TOTAL_MASS_DISTRIBUTION_STEP, \
    MAX_CONSECUTIVE_NULL_IMPACT_CHARACTERIZED_INGREDIENTS_MASS, MINIMUM_TOTAL_MASS_FOR_UNBALANCED_RECIPES, \
    OFF_INGREDIENTS_FORMAT
from data import ref_ing_dist, ingredients_data
from impacts_estimation.exceptions import RecipeCreationError, NoKnownIngredientsError, SolverTimeoutError, \
    NoCharacterizedIngredientsError

ing_with_ref_prct_dist = list(ref_ing_dist.id.unique())


class RecipeImpactCalculator:
    def __init__(self, recipe, impact_name, use_uncertainty=False):
        """

        Args:
            recipe (dict): Dict containing ingredients as keys and masses in grams as values
            impact_name (str): Name of the impact as in ingredients_data.json
            use_uncertainty (bool): Should the ingredients uncertainty data be used to pick a randomized impact value?
            If True, the result may vary from one call to another.
        """
        self.recipe = recipe
        self.impact_name = impact_name
        self.use_uncertainty = use_uncertainty
        self.ingredients_impacts = dict()
        self.known_ingredients_mass = None
        self.known_ingredients_impact = None

        self.impact_computed = False
        self.impact_shares_computed = False

        self._define_ingredients_impacts()

    def _define_ingredients_impacts(self):
        """
        Getting the impact of each ingredient. If the ingredient has no uncertainty parameters or use_uncertainty is
        set to False, simply use the default value. Else pick a value using the uncertainty parameters.
        """

        for ingredient in self.recipe:
            try:
                ingredient_impact_data = ingredients_data[ingredient]['impacts'][self.impact_name]
            except KeyError:
                continue
            rng = np.random.default_rng()
            if ('uncertainty_distributions' not in ingredient_impact_data) or (not self.use_uncertainty):
                self.ingredients_impacts[ingredient] = ingredient_impact_data['amount']
            else:
                # Pick a random uncertainty distribution
                uncertainty_distribution = choice(ingredient_impact_data['uncertainty_distributions'])
                if uncertainty_distribution['distribution'] == 'normal':
                    self.ingredients_impacts[ingredient] = rng.normal(uncertainty_distribution['mean'],
                                                                      uncertainty_distribution['standard deviation'])
                elif uncertainty_distribution['distribution'] == 'lognormal':
                    if uncertainty_distribution['geometric mean'] >= 0:
                        # Numpy requires the mean and std of the underlying normal distribution, which are the logs of
                        # the mean and std of the lognormal distribution.
                        self.ingredients_impacts[ingredient] = rng.lognormal(
                            np.log(uncertainty_distribution['geometric mean']),
                            np.log(uncertainty_distribution['geometric standard deviation']))
                    # If the geometric mean is negative, then simply take the opposite of the value generated
                    # with the opposite of the geometric mean
                    if uncertainty_distribution['geometric mean'] < 0:
                        self.ingredients_impacts[ingredient] = - rng.lognormal(
                            np.log(-uncertainty_distribution['geometric mean']),
                            np.log(uncertainty_distribution['geometric standard deviation']))
                elif uncertainty_distribution['distribution'] == 'triangular':
                    self.ingredients_impacts[ingredient] = rng.triangular(uncertainty_distribution['minimum'],
                                                                          uncertainty_distribution['mode'],
                                                                          uncertainty_distribution['maximum'])
                elif uncertainty_distribution['distribution'] == 'uniform':
                    self.ingredients_impacts[ingredient] = rng.uniform(uncertainty_distribution['minimum'],
                                                                       uncertainty_distribution['maximum'])
                else:
                    raise ValueError(f"Unknown distribution type {uncertainty_distribution['distribution']}"
                                     f" for ingredient {ingredient}")

    def _compute_impact(self):
        # Computing the impact of the recipe
        self.known_ingredients_impact = 0
        self.known_ingredients_mass = 0
        self.total_mass = sum([float(x) for x in self.recipe.values()])

        # Looping on all ingredients that has a value for the considered impact
        for ingredient_name, ingredient_impact in self.ingredients_impacts.items():
            # Adding the ingredient to the known ingredients mass
            self.known_ingredients_mass += float(self.recipe[ingredient_name])

            # Adding the impact to the result
            self.known_ingredients_impact += float(self.recipe[ingredient_name]) * ingredient_impact / IMPACT_MASS_UNIT

        if self.known_ingredients_mass == 0:
            self._recipe_impact = None
        else:
            # Inflating the impact of the known ingredients to the impact of the total mass of these ingredients
            self._recipe_impact = self.known_ingredients_impact * self.total_mass / self.known_ingredients_mass

        self.impact_computed = True

    def _compute_impact_shares(self):

        # Compute impact if it has not been done yet
        if not self.impact_computed:
            self._compute_impact()

        # Computing the impact share for each ingredient
        self.ingredients_impacts_shares = dict()
        if self.known_ingredients_mass != 0:
            for ingredient_name, ingredient_mass in self.recipe.items():

                if ingredient_name in self.ingredients_impacts:
                    ingredient_impact = self.ingredients_impacts[ingredient_name]

                    self.ingredients_impacts_shares[ingredient_name] = \
                        (ingredient_impact * ingredient_mass / IMPACT_MASS_UNIT) / self._recipe_impact
                else:
                    self.ingredients_impacts_shares[ingredient_name] = ingredient_mass / self.total_mass

        self.impact_shares_computed = True

    def get_recipe_impact(self):
        """
        Calculate the environmental impact from a product recipe.

        Warning:
            Any ingredients whose impact is unknown will be considered to have the average impact of the product.

        Returns:
            float: Impact of the product
        """

        # Compute impact if it has not been done yet
        if not self.impact_computed:
            self._compute_impact()

        return self._recipe_impact

    def get_ingredient_impact_share(self, ingredient):
        """ Returns the share of the recipe impact that is due to the given ingredient """

        # Compute impact if it has not been done yet
        if not self.impact_shares_computed:
            self._compute_impact_shares()

        if ingredient not in self.recipe:
            return ValueError('The ingredient is not present in the recipe.')

        # If the recipe impact is None, then there is no result
        if self._recipe_impact is None:
            return None

        return self.ingredients_impacts_shares[ingredient]


def impact_from_recipe(recipe, impact_name, use_uncertainty=False):
    """ Wrapper for RecipeImpactCalculator """
    recipe_impact_calculator = RecipeImpactCalculator(recipe=recipe,
                                                      impact_name=impact_name,
                                                      use_uncertainty=use_uncertainty)

    return recipe_impact_calculator.get_recipe_impact()


class RandomRecipeCreator:

    def __init__(self, product, use_defined_prct=True, use_nutritional_info=True, const_relax_coef=0,
                 maximum_evaporation=0.4, total_mass_used=None, min_prct_dist_size=30, dual_gap_type='absolute',
                 dual_gap_limit=0.001, solver_time_limit=60, time_limit_dual_gap_limit=0.01,
                 allow_unbalanced_recipe=False, confidence_score_weighting_factor=10):
        """
        Args:
            product (dict): Dict containing an OpenFoodFact product.
                It must contain the keys "ingredients" and "nutriments"
            use_defined_prct (bool): Should ingredients percentages defined in the product be used?
            use_nutritional_info (bool): Should nutritional information be used to estimate recipe?
            const_relax_coef (float): Constraints relaxation coefficient. Allows to relax constraints on nutriments,
                water and mass balance to increase chances to get a result.
            maximum_evaporation (float): Upper bound of the evaporation coefficient [0-1[. I.e. maximum proportion of
                ingredients water that can evaporate.
            total_mass_used (float): Total mass of ingredient used in grams, if known.
            min_prct_dist_size (int): Minimum size of the ingredients percentage distribution that will be used to pick
                a proportion for an ingredient. If the distribution (adjusted to the possible value interval) has less
                data, uniform distribution will be used instead.
            dual_gap_type (str): 'absolute' or 'relative'. Determines the precision type of the variable optimization
                by the solver.
            dual_gap_limit (float): Determines the precision of the variable optimization by the solver.
                Relative or absolute according to dual_gap_type.
            solver_time_limit (float): Maximum time for the solver optimization (in seconds).
                Set to None or 0 to set no limit.
            time_limit_dual_gap_limit (float): Accepted precision of the solver in case of time limit hit.
                Relative or absolute according to dual_gap_type.
            allow_unbalanced_recipe (bool): If True, the total mass of ingredients used in the resulting recipe may be
                less than the final mass of the product. This is not physically possible but may be necessary to avoid
                systematical overestimation of the total mass of ingredients used.
            confidence_score_weighting_factor (float): Weighting factor used for the confidence score calculation.
                It corresponds to the weight of the nutritional distance against the absolute difference between the
                 total mass and 100g/100g.
        """
        self.product = product
        self.use_defined_prct = use_defined_prct
        self.use_nutritional_info = use_nutritional_info
        self.const_relax_coef = const_relax_coef
        self.min_dist_size = min_prct_dist_size
        self.total_mass_used = total_mass_used
        individualize_ingredients(self.product)
        self.top_level_ingredients = product['ingredients']
        self.top_level_ingredients_names = [x['id'] for x in self.top_level_ingredients]
        self.leaf_ingredients = find_ingredients_graph_leaves(self.product)
        self.leaf_ingredients_names = [x['id'] for x in self.leaf_ingredients]
        self.all_ingredients = flat_ingredients_list_BFS(self.product)
        self.all_ingredients_names = [x['id'] for x in self.all_ingredients]
        self.decreasing_order_limit_rank = None
        self.dual_gap_type = dual_gap_type.lower()
        self.time_limit_dual_gap_limit = time_limit_dual_gap_limit
        self.allow_unbalanced_recipe = allow_unbalanced_recipe
        self.maximum_evaporation = maximum_evaporation
        self.confidence_score_weighting_factor = confidence_score_weighting_factor

        self.recipe = dict()

        # Defining a solver that will be used to define the range of possible recipes
        self.model = Model()
        if VERBOSITY < 3:
            self.model.hideOutput()

        if solver_time_limit:
            self.model.setParam('limits/time', solver_time_limit)

        if self.dual_gap_type == 'absolute':
            self.model.setParam('limits/absgap', dual_gap_limit)
        elif self.dual_gap_type == 'relative':
            self.model.setParam('limits/gap', dual_gap_limit)
        else:
            raise ValueError("The parameter dual_gap_type should be 'absolute' or 'relative'.")

        # Adding variables to the solver
        # Adding a variable for the total mass of ingredients used
        self.total_mass_var = self.model.addVar('total_mass_used',
                                                vtype='C',
                                                lb=MINIMUM_TOTAL_MASS_FOR_UNBALANCED_RECIPES
                                                if self.allow_unbalanced_recipe else 1)

        # If the total mass used is provided, add it as a constraint
        if self.total_mass_used is not None:
            self.model.addCons(self.total_mass_var == self.total_mass_used / 100)

        # The evaporation coefficient is one variable of the solver describing how much of the unprocessed ingredients
        # water is lost during food processing. It is not bounded to 1 to avoid infinite value of the total mass used.
        assert 0 <= maximum_evaporation < 1
        self.evaporation_var = self.model.addVar('evaporation', vtype="C", lb=0, ub=self.maximum_evaporation)

        # INGREDIENTS VARIABLES
        # One variable per ingredient, corresponding to its proportion of the ingredients masses used
        self.ingredient_vars = dict()
        for ingredient_name in self.all_ingredients_names:
            self.ingredient_vars[ingredient_name] = self.model.addVar(ingredient_name, vtype="C", lb=0, ub=1)

        # If water is not present in the ingredient list, add it as water under 5% hasn't to be declared
        if 'en:water' not in self.top_level_ingredients_names:
            # Water may be in leaf ingredients but not in top level ingredients, in that case it must be individualized
            water_name = 'en:water'
            while water_name in self.leaf_ingredients_names:
                water_name += '*'
            self.ingredient_vars[water_name] = self.model.addVar(water_name, vtype="C", lb=0, ub=0.05)
            self.leaf_ingredients_names.append(water_name)

        # Creating a dict with ingredients nutritional data
        self.ingredients_data = dict()
        for ingredient_name in self.leaf_ingredients_names:
            if ingredient_name not in self.ingredients_data:
                self.ingredients_data[ingredient_name] = dict()
            for nutri_item in NUTRIMENTS_CATEGORIES + ['water', 'ash']:
                if (original_id(ingredient_name) in ingredients_data) \
                        and (nutri_item in ingredients_data[original_id(ingredient_name)].get('nutriments', [])):
                    self.ingredients_data[ingredient_name][nutri_item] = \
                        ingredients_data[original_id(ingredient_name)]['nutriments'][nutri_item]
                else:
                    # Giving default minimum and maximum nutriment/water content (0 and 100%) to unknown ingredients
                    self.ingredients_data[ingredient_name][nutri_item] = {'min': 0,
                                                                          'max': MAX_ASH_CONTENT if nutri_item == 'ash'
                                                                          else 100}

    def _add_used_mass_constraint(self):
        """ Adding the constraint that the total used mass of ingredients is bounded by the evaporation coefficient. """

        # Lower bound is already set in total_mass_var definition

        # Upper bound
        self.model.addCons(self.total_mass_var <= 1 / (1 - self.evaporation_var),
                           name="Used mass bound")

    def _add_total_leaves_percentage_constraint(self):
        """ The sum of the percentages of all leaf ingredients must be 100%. """

        # Sum of the leaves
        self.model.addCons(sum([self.ingredient_vars[x] for x in self.leaf_ingredients_names]) == 1,
                           name="Total percentage is 100%")

    def _add_total_subingredients_percentages_constraint(self, ingredient):
        """
        Recursive function to add for each compound ingredient the constraint that its percentage must equal the sum
        of the percentages of its subingredients.

        Args:
            ingredient (dict): Dict corresponding to a compound ingredient.
        """

        if 'ingredients' in ingredient:
            # Adding the constraint
            self.model.addCons(sum([self.ingredient_vars[x['id']] for x in ingredient['ingredients']])
                               == self.ingredient_vars[ingredient['id']],
                               name=f"Subingredients sum for {ingredient['id']}")

            # Recursive call for the subingredients
            for subingredient in ingredient['ingredients']:
                self._add_total_subingredients_percentages_constraint(subingredient)

    def _add_mass_order_constraints(self, product):
        """
        Recursive function to add the constraint that each (sub)ingredient must be in higher proportion than the
        next one of the same level.

        Args:
            product (dict): Dict corresponding to a product or a compound ingredient.
        """
        if 'ingredients' in product:
            for i in range(len(product['ingredients']) - 1):
                ing_var = self.ingredient_vars[product['ingredients'][i]['id']]
                next_ing_var = self.ingredient_vars[product['ingredients'][i + 1]['id']]

                self.model.addCons(next_ing_var <= ing_var, name=f"{product['ingredients'][i]['id']}>="
                                                                 f"{product['ingredients'][i + 1]['id']}")

            # Recursive call for the subingredients
            for ingredient in product['ingredients']:
                self._add_mass_order_constraints(ingredient)

    def _add_evaporation_constraint(self):
        """
        The product mass is bounded by:
            - Lower bound: The sum of the ingredients masses used multiplied by 1 minus the water they lost
                (evaporation coefficient multiplied by water content of the ingredient). Ingredients with unknown water
                content are supposed to have a water content of 1 for lower bound.
            - Upper bound: The sum of the ingredients masses used multiplied by 1 minus the water they lost
                (evaporation coefficient multiplied by water content of the ingredient) for ingredients with a known
                water content, plus the sum of ingredients with unknown water content masses (as they water content is
                supposed to be 0 for upper bound)
        """

        # Lower bound
        self.model.addCons(
            self.total_mass_var * (1 - self.evaporation_var * (
                sum([self.ingredient_vars[ing] * self.ingredients_data[ing]['water']['max'] / 100
                     for ing in self.ingredient_vars
                     if ing in self.leaf_ingredients_names])
            ))
            <= (1 + self.const_relax_coef),
            name="Product mass evaporation lower bound"
        )

        # Upper bound
        self.product_mass_evaporation_upper_bound_constraint = \
            self.model.addCons(
                self.total_mass_var * (1 - self.evaporation_var * (
                    sum([self.ingredient_vars[ing] * self.ingredients_data[ing]['water']['min'] / 100
                         for ing in self.ingredient_vars
                         if ing in self.leaf_ingredients_names])
                ))
                >= (1 - self.const_relax_coef),
                name="Product mass evaporation upper bound"
            )

    def _add_product_mass_constraint(self):
        """ The product mass is bounded by the sum of all nutriments and the remaining water """

        # Lower bound
        self.model.addCons(
            self.total_mass_var * (
                sum([
                    self.ingredient_vars[ingredient] *
                    (((1 - self.evaporation_var) * self.ingredients_data[ingredient]['water']['min'] / 100) +
                     sum([self.ingredients_data[ingredient][nutriment]['min'] / 100
                          for nutriment in TOP_LEVEL_NUTRIMENTS_CATEGORIES + ['ash']]))
                    for ingredient in self.leaf_ingredients_names
                ])
            )
            <= (1 + self.const_relax_coef),
            name="Product mass upper bound"
        )

        # Upper bound
        self.model.addCons(
            self.total_mass_var * (
                sum([self.ingredient_vars[ingredient] *
                     (((1 - self.evaporation_var) * self.ingredients_data[ingredient]['water']['max'] / 100) +
                      sum([self.ingredients_data[ingredient][nutriment]['max'] / 100
                           for nutriment in TOP_LEVEL_NUTRIMENTS_CATEGORIES + ['ash']]))
                     for ingredient in self.leaf_ingredients_names])
            )
            >= (1 - self.const_relax_coef),
            name="Product mass upper bound"
        )

    def _add_nutritional_constraints(self):
        """
        Looping on all nutriments to add the constraint that the sum of the ingredients proportions weighted by
        their content in this nutriment must fit the nutritional content of the product.
        """

        # Looping on nutrients
        for nutri_item in NUTRIMENTS_CATEGORIES:
            if nutri_item == 'other':
                continue

            # Checking that the product has no data quality warnings related to this nutrient
            if len([x for x in QUALITY_DATA_WARNINGS.get(nutri_item, [])
                    if x in self.product.get('data_quality_tags', [])]) > 0:
                continue

            # Check if the product has this nutriment defined
            product_nutriment = self.product['nutriments'].get(nutri_item + '_100g')
            if product_nutriment is None:
                continue
            else:
                product_nutriment = float(product_nutriment)

            margins = nutritional_error_margin(nutriment=nutri_item, value=product_nutriment / 100)
            absolute_margin = margins['absolute']
            relative_margin = margins['relative']

            # Lower bound
            self.model.addCons(
                ((absolute_margin + (1 + relative_margin) * product_nutriment / 100) + self.const_relax_coef)
                >=
                (self.total_mass_var *
                 sum([var * self.ingredients_data[name][nutri_item]['min'] / 100
                      for name, var in self.ingredient_vars.items()
                      if name in self.leaf_ingredients_names])),
                name=f"Lower bound for {nutri_item}"
            )

            # Upper bound
            self.model.addCons(
                ((-absolute_margin + (1 - relative_margin) * product_nutriment / 100) - self.const_relax_coef)
                <=
                (self.total_mass_var *
                 (sum([var * self.ingredients_data[name][nutri_item]['max'] / 100
                       for name, var in self.ingredient_vars.items()
                       if name in self.leaf_ingredients_names]))
                 ),
                name=f"Upper bound for {nutri_item}"
            )

    def _add_defined_percentage_constraints(self, product):
        """
        Recursive function to add the constraints corresponding to the defined (sub)ingredients percentages.
        For top-level ingredients, defined percentages correspond to the percentage of the total mass of ingredients
        used before processing. For subingredients, the percentage corresponds either to the percentage of the parent
        ingredient or to the percentage of the product. This is determined by a preprocessing step made by
        ImpactEstimator._check_multilevel_ingredients. In cases where the percentage type is undefined, it is ignored.

        Args:
            product (dict): Dict corresponding to a product or a compound ingredient.
        """

        for rank, ingredient in enumerate(product['ingredients']):
            if ingredient.get('percent'):  # If the ingredient has a non null 'percent' field
                try:
                    proportion = float(ingredient['percent']) / 100

                    if (product.get('percent-type') == 'product') \
                            or (product is self.product):  # For top level ingredients
                        self.model.addCons(self.ingredient_vars[ingredient['id']] == proportion,
                                           name=f"{ingredient['id']}: {ingredient['percent']}% of product")

                    elif product.get('percent-type') == 'parent':
                        self.model.addCons(self.ingredient_vars[ingredient['id']]
                                           ==
                                           proportion * self.ingredient_vars[product['id']],
                                           name=f"{ingredient['id']}: {ingredient['percent']}% of parent")

                    # Ingredients which percentage is lower than 2% does not need to be listed in decreasing
                    # proportion order. If the percentage of the ingredient is lower than 2%, then replace the
                    # decreasing proportion order constraint by a 2% maximum constraint for all following
                    # ingredients. This is done only for top level ingredients.
                    if (proportion <= DECREASING_PROPORTION_ORDER_LIMIT) \
                            and (product is self.product):
                        self._remove_decreasing_order_constraint_from_rank(rank)

                except ValueError:  # To pass errors in float casting
                    pass

            # Recursive call for the subingredients
            if 'ingredients' in ingredient:
                self._add_defined_percentage_constraints(ingredient)

    def _remove_decreasing_order_constraint_from_rank(self, rank):
        """
        Removes the decreasing proportion order constraint for all ingredients from the given rank.
        If an ingredient is below a certain proportion (2% in EU regulation), it may not be indicated in decreasing
        proportion order.

        Args:
            rank (int): Rank of the ingredient from which the decreasing proportion order constraint shall be replaced
                by a maximum proportion constraint.
        """
        if rank < (self.decreasing_order_limit_rank or len(self.top_level_ingredients)):
            # Removing constraints
            for r in range(rank, len(self.top_level_ingredients) - 1):
                constraint = [x for x in self.model.getConss()
                              if x.name == f"{self.top_level_ingredients_names[r]}>="
                                           f"{self.top_level_ingredients_names[r + 1]}"]

                # Checking if the constraint exists as the solver may have deleted it by itself
                if constraint:
                    self.model.freeTransform()
                    self.model.delCons(constraint[0])

            # Adding maximum constraint :
            for r in range(rank + 1, len(self.top_level_ingredients)):
                self.model.freeTransform()
                self.model.addCons(self.ingredient_vars[self.top_level_ingredients_names[r]]
                                   <=
                                   DECREASING_PROPORTION_ORDER_LIMIT,
                                   name=f"{self.top_level_ingredients_names[r]}<=2%")

            self.decreasing_order_limit_rank = rank

    def _optimize_variable(self, variable, direction='minimize'):
        """
        Optimize the model and return the variable value.

        Args:
            variable (Variable): Variable to optimize
            direction (str): 'minimize' or 'maximize'

        Returns:
            float: Value of the optimized variable.
        """

        if direction.lower() not in ('minimize', 'maximize'):
            raise ValueError

        self.model.freeTransform()
        self.model.setObjective(variable if direction.lower() == 'minimize' else -variable)
        self.model.optimize()
        if self.model.getStatus() not in ('optimal', 'gaplimit', 'timelimit'):
            raise RecipeCreationError

        # In case of time limit hit, check if the gap is higher than the gap tolerance for time limit
        if self.model.getStatus() == 'timelimit':
            gap = self.model.getGap()
            if self.dual_gap_type == 'absolute':
                if gap > self.time_limit_dual_gap_limit:
                    raise SolverTimeoutError
            elif self.dual_gap_type == 'relative':
                if gap > self.time_limit_dual_gap_limit * self.model.getDualbound():
                    raise SolverTimeoutError

        return self.model.getVal(variable)

    def _get_variable_bounds(self, variable):
        """
        Use the solver to find the ingredient's lower and upper bound.

        Args:
            variable (Variable): Solver variable

        Returns:
            tuple: Tuple containing ingredient lower and upper bounds
        """

        sup = self._optimize_variable(variable, direction='maximize')
        inf = self._optimize_variable(variable, direction='minimize')

        return inf, sup

    def _pick_proportion(self, ingredient_name, inf, sup):
        """
        Chooses a random proportion for this ingredient.

        Uses a reference percentage distribution if the distribution of this ingredient in this interval has enough
        data, else uses an uniform distribution.

        Args:
            ingredient_name (str):
            inf (float): Lower bound
            sup (float): Upper bound

        Returns:
            float: Proportion of this ingredient
        """

        assert round(inf, 8) <= round(sup, 8)  # Rounded values used to avoid precision errors

        # If the two bounds are the same, return it as percentage
        if round(inf, 8) == round(sup, 8):
            return inf

        # Converting from proportion to percentages (as reference distributions use percentages)
        inf, sup = inf * 100, sup * 100

        # If the ingredient has a reference percentage distribution, use it, else use a uniform distribution
        if ingredient_name in ing_with_ref_prct_dist:

            # Getting the reference percentage distribution of this ingredient
            reference_distribution = ref_ing_dist[ref_ing_dist.id == ingredient_name]

            # Stripping the values outside of the interval of possible solutions
            reference_distribution = reference_distribution[inf <= reference_distribution.percent]
            reference_distribution = reference_distribution[reference_distribution.percent <= sup]

            # If the product has categories, looping on it from the most specific to the most general and
            # stopping the loop when there are enough data in the reference distribution of the ingredient for
            # this category. If no category has enough data, use the entire distribution. If the entire
            # distribution does not have enough data, use a uniform distribution.

            if self.product.get('categories_tags'):  # If the product has a non empty category tags
                category_distribution = []
                category_index = len(self.product['categories_tags'])
                while (len(category_distribution) < self.min_dist_size) and (category_index >= 0):
                    category_index -= 1
                    category = self.product['categories_tags'][category_index]
                    mask = reference_distribution.categories_tags.apply(lambda x: category in (x or []))
                    category_distribution = reference_distribution[mask]

                if len(category_distribution) >= self.min_dist_size:
                    reference_distribution = category_distribution

            # If there are less values than required, use uniform distribution
            if len(reference_distribution) < self.min_dist_size:
                percent = uniform(inf, sup)
            else:
                bandwidth = (sup - inf) / 10
                kde = KernelDensity(kernel='gaussian', bandwidth=bandwidth)
                kde.fit(reference_distribution.percent.values.reshape(-1, 1))

                # Plotting the KDE for debug purpose, comment on production
                # x_plot = np.linspace(inf - 5 * bandwidth, sup + 5 * bandwidth, 1000)[:, np.newaxis]
                # y_plot = np.exp(kde.score_samples(x_plot))
                #
                # fig, ax = plt.subplots()
                #
                # # Plotting distribution
                # ax.plot(x_plot, y_plot)
                # # Plotting data points
                # ax.scatter(reference_distribution.percent.values, np.zeros(len(reference_distribution)),
                #            marker='+', alpha=0.2, color='darksalmon')
                # # Plotting the bounds
                # ax.axvline(sup, color="seagreen", linestyle="dashed", linewidth=4)
                # ax.axvline(inf, color="seagreen", linestyle="dashed", linewidth=4)
                #
                # ax.set_title(
                #     f"{ingredient_name} - bw:{round(bandwidth, 2)} - density:{round(len(reference_distribution) / (sup - inf))}")
                #
                # plt.show()

                # Ensure the sampled value is between inf and sup
                percent = -1
                while (percent < inf) or (percent > sup):
                    percent = kde.sample()[0][0]

        else:
            percent = uniform(inf, sup)

        return percent / 100  # Converting back to proportion

    @staticmethod
    def recipe_from_proportions(proportions, total_mass):
        """
        Returns a recipe from ingredients proportions and a total mass.
        Sums masses of ingredients used multiple times.

        Args:
            proportions (dict):
            total_mass (float):

        Returns:
            dict:
        """
        ingredients_names = set()

        for name in proportions:
            ingredients_names.add(original_id(name))

        return {name: sum([prop
                           for name_2, prop in proportions.items()
                           if original_id(name_2) == name]) * total_mass
                for name in ingredients_names}

    def _pick_total_mass(self, proportions):
        """
        Choosing the total mass of ingredients used by maximizing the confidence score of the resulting recipe.

        Args:
            proportions (dict): Proportions of the ingredients.

        Returns:
            float: Total mass of ingredients used in g.
        """

        if self.total_mass_used is not None:
            return self.total_mass_used

        # Getting the total mass variable bounds
        inf, sup = self._get_variable_bounds(self.total_mass_var)

        # If the difference between the two bounds is lower than the distribution step, simply return the mean value
        if (sup - inf) <= (TOTAL_MASS_DISTRIBUTION_STEP / 100):
            return 100 * (sup + inf) / 2

        # Looping over the total masses ranges with a predefined step and computing the confidence score of each
        # resulting recipe
        max_conf_score = 0
        result = inf

        # ### FOR DEBUG PURPOSE ONLY ###
        # total_masses = []
        # conf_scores = []
        # ##############################

        # Compute the total mass only if nutritional info are used and there is at least one top level category
        # nutriment in common
        recipe = self.recipe_from_proportions(proportions, inf * 100)
        recipe_nutriments = nutriments_from_recipe(recipe)
        if self.use_nutritional_info and any([f"{x}_100g" in self.product['nutriments']
                                              for x in recipe_nutriments
                                              if x in TOP_LEVEL_NUTRIMENTS_CATEGORIES]):
            for total_mass in np.arange(inf, sup, TOTAL_MASS_DISTRIBUTION_STEP / 100):
                recipe = self.recipe_from_proportions(proportions, total_mass * 100)
                recipe_nutriments = nutriments_from_recipe(recipe)

                # In some cases, the total mass is too high and will give impossible nutritional composition, in that
                # case the confidence score calculation will raise a ValueError
                try:
                    conf_score = confidence_score(nutri=recipe_nutriments,
                                                  reference_nutri=self.product['nutriments'],
                                                  total_mass=total_mass * 100,
                                                  min_possible_mass=MINIMUM_TOTAL_MASS_FOR_UNBALANCED_RECIPES * 100
                                                  if self.allow_unbalanced_recipe else 100,
                                                  max_possible_mass=100 / (1 - self.maximum_evaporation),
                                                  weighting_factor=self.confidence_score_weighting_factor)
                except ValueError:
                    continue

                # ### FOR DEBUG PURPOSE ONLY ###
                # total_masses.append(total_mass)
                # conf_scores.append(conf_score)
                # ##############################

                # If the conf score is higher than the max, update the result and the max
                if conf_score > max_conf_score:
                    max_conf_score = conf_score
                    result = total_mass

        # ### FOR DEBUG PURPOSE ONLY ###
        # plt.plot(total_masses, conf_scores)
        # plt.show()
        # ##############################

        result *= 100

        return result

    def random_recipe(self):
        """
        Create a possible recipe of a product given its ingredient list and nutritional data.
        The recipe is given for 100g of final product.

        Notes:
            The recipe of the product is estimated randomly. To do this, a linear programming solver is defined
            with these constraints:
                - the sum of all ingredients percentage must be 100;
                - the ingredients percentages are given in decreasing order;
                - the nutritional composition of the product is the sum of the nutritional composition of its
                    ingredients (with an error margin specified by nutritional_info_precision);
                - some ingredients may have a defined percentage.
            Once the solver has been set, the algorithm loops through each ingredient in random order, and computes its
            possible values interval using the solver. Once the possibles values interval defined, it chooses a random
            proportion value for this ingredient within this interval and adds this value as a new constraint for the
            solver. If the ingredient has a reference percentage distribution (computed from existing OFF data), the
            random value will be picked following this distribution. If not, it will use a uniform distribution.
            Once all ingredients proportions have been defined, the same operation is done on the total mass used
            variable, by maximizing the confidence score of the resulting recipe.

        Returns:
            dict: Dictionary containing a possible recipe with ingredients ids as keys and masses in g as values.
        """

        # Setting variables
        self.recipe = dict()  # Resetting the recipe

        # Removing previous constraints
        self.model.freeTransform()
        for constraint in self.model.getConss():
            self.model.delCons(constraint)

        # Adding constraints to the solver
        self._add_used_mass_constraint()
        self._add_total_leaves_percentage_constraint()
        for ingredient in self.top_level_ingredients:
            self._add_total_subingredients_percentages_constraint(ingredient)
        self._add_mass_order_constraints(self.product)
        self._add_evaporation_constraint()

        total_mass_lower_bound_constraint = self.model.addCons(self.total_mass_var >= 0.99,
                                                               'Total mass lower bound')

        # Checking that the product has no global data quality warnings related to nutrition before adding nutritional
        # constraints
        global_dqw = [x for x in QUALITY_DATA_WARNINGS['global'] if x in self.product.get('data_quality_tags', [])]
        if self.use_nutritional_info and not global_dqw:
            self._add_nutritional_constraints()
            self._add_product_mass_constraint()

        if self.use_defined_prct:
            self._add_defined_percentage_constraints(self.product)

        # Shuffling the ingredients
        leaf_ingredients_names = self.leaf_ingredients_names.copy()  # Creating a copy to avoid messing with original
        shuffle(leaf_ingredients_names)

        # Looping over ingredients to pick a random proportion in their possible values interval
        proportions = dict()
        for ingredient_name in leaf_ingredients_names:
            inf, sup = self._get_variable_bounds(self.ingredient_vars[ingredient_name])

            # Now the possible values interval has been calculated,
            # choose a random proportion within it for this ingredient
            proportion = self._pick_proportion(ingredient_name, inf, sup)

            proportions[ingredient_name] = proportion

            # Adding the choice of this value as a constraint to the problem
            self.model.freeTransform()
            self.model.addCons(self.ingredient_vars[ingredient_name] == proportion,
                               name=f"{ingredient_name}: {proportion}")

            if (proportion <= DECREASING_PROPORTION_ORDER_LIMIT) \
                    and (ingredient_name in self.top_level_ingredients_names):
                self._remove_decreasing_order_constraint_from_rank(
                    self.top_level_ingredients_names.index(ingredient_name))

        if self.allow_unbalanced_recipe:
            self.model.freeTransform()
            self.model.delCons(total_mass_lower_bound_constraint)
            self.model.delCons(self.product_mass_evaporation_upper_bound_constraint)

        total_mass = self._pick_total_mass(proportions)

        self.recipe = self.recipe_from_proportions(proportions, total_mass)

        if VERBOSITY >= 2:
            print(self.recipe)

        return self.recipe


class ImpactEstimator:
    def __init__(self, product, quantity=100, ignore_unknown_ingredients=True, use_defined_prct=True):

        """
        Estimate the environmental impact of an Open Food Facts product by a Monte-Carlo approach.

        Notes:
            This algorithm is composed of a loop that will calculate the impacts of the product based on its
            ingredients. At each run of the loop, the impact values are stored and the loop ends either if the maximum
            number of runs have been reached or if the geometric mean of each computed impact values is stabilized
            within a given confidence interval.

            The impact values are calculated by doing a simple sum of all ingredients masses weighted by their own
            impact values acquired from external data.

        Args:
            product (dict): Dict containing an Open Food Facts product. It must contain the keys "ingredients"
            quantity (float): Quantity of product in grams for which the impact must be calculated. Default is 100g.
            ignore_unknown_ingredients (bool): Should ingredients absent of OFF taxonomy and without defined percentage
                be considered as parsing errors and ignored?
            use_defined_prct (bool): Should ingredients percentages defined in the product be used?
        """

        self.start_time = time.time()
        self.product = copy.deepcopy(product)
        self.ignore_unknown_ingredients = ignore_unknown_ingredients
        self.ignored_unknown_ingredients = []
        self.product_quantity = quantity
        self.adjusted_maximum_evaporation_coefficient = None

        # Assert the product has ingredients
        if 'ingredients' not in product:
            raise AttributeError("The product has no ingredients field.")
        if len(product['ingredients']) == 0:
            raise ValueError("The product ingredients list is empty.")

        # List of text warnings to characterize the result in some special cases (too many unknown ingredients for
        #  example)
        self.warnings = []

        # Performing checks on product type
        self._check_fermented_product()
        self._check_product_water_loss()

        # Performing checks for multilevel ingredients
        self._check_ingredients()

        # Performing checks on the uncharacterized ingredients (ingredients with no nutrition and/or impact data)
        self.leaf_ingredients = find_ingredients_graph_leaves(self.product)
        self.nb_ing = len(self.leaf_ingredients)
        self.use_defined_prct_arg = use_defined_prct
        self.use_defined_prct = use_defined_prct
        self.uncharacterized_ingredients = {
            'nutrition': [x for x in self.leaf_ingredients
                          if 'nutriments'
                          not in ingredients_data.get(original_id(x['id']), [])],
            'impact': [x for x in self.leaf_ingredients
                       if 'impacts'
                       not in ingredients_data.get(original_id(x['id']), [])]
        }
        self.uncharacterized_ingredients_ids = {
            'nutrition': list(set([original_id(x['id'])
                                   for x in
                                   self.uncharacterized_ingredients['nutrition']])),
            'impact': list(set([original_id(x['id'])
                                for x in
                                self.uncharacterized_ingredients['impact']]))
        }
        # Lists that will store the mass of uncharacterized ingredients for each recipe
        self.uncharacterized_ingredients_mass_distribution = {'nutrition': [], 'impact': []}
        self.uncharacterized_ingredients_ratio = {
            'nutrition': len(self.uncharacterized_ingredients['nutrition']) / self.nb_ing,
            'impact': len(self.uncharacterized_ingredients['impact']) / self.nb_ing,
        }

        for characterization in 'nutrition', 'impact':
            if self.uncharacterized_ingredients_ratio[characterization] >= \
                    UNCHARACTERIZED_INGREDIENTS_RATIO_WARNING_THRESHOLD:
                self.warnings.append(
                    f"The product has a high number of {characterization} uncharacterized ingredients: "
                    f"{self.uncharacterized_ingredients_ratio[characterization]:.0%}")

        # Assert that the product has nutriments. If not add a warning and set use_nutritional_info_override to False
        self.use_nutritional_info_override = None
        if ('nutriments' not in product) \
                or (all([f"{x}_100g" not in product.get('nutriments', dict()) for x in NUTRIMENTS_CATEGORIES])):
            self.use_nutritional_info_override = False
            self.warnings.append("The product has no recognized nutriment information.")

        # Perform checks on defined percentages of ingredients
        self._check_defined_percentages()

    def _check_fermented_product(self):
        """
            Checks if the product is fermented (alcohol or cheese for example).
            In that case, the carbohydrates should not be taken into account as the carbohydrates input of the
            ingredients may not be the same than the output in the product.
        """
        identified_fermentation_agents = [x['id'] for x in flat_ingredients_list_BFS(self.product)
                                          if x['id'] in FERMENTATION_AGENTS]

        if identified_fermentation_agents:
            self.warnings.append(f"Fermentation agents are present in the product "
                                 f"({', '.join(identified_fermentation_agents)}). "
                                 f"Carbohydrates and sugars mass balance will not be considered to estimate potential "
                                 f"recipes")

        identified_fermented_product_categories = [x for x in self.product.get('categories_tags', [])
                                                   if x in FERMENTED_FOOD_CATEGORIES]

        if identified_fermented_product_categories:
            self.warnings.append(f"The product belongs to fermented products categories "
                                 f"({', '.join(identified_fermented_product_categories)}). "
                                 f"Carbohydrates and sugars mass balance will not be considered to estimate potential "
                                 f"recipes")

        if identified_fermentation_agents or identified_fermented_product_categories:
            for nutrition_item_to_delete in ('carbohydrates', 'sugars'):
                try:
                    del self.product['nutriments'][f"{nutrition_item_to_delete}_100g"]
                except KeyError:
                    pass

    def _check_product_water_loss(self):
        """
           Some products (cheeses for example) may have a bigger water loss than other. If the product is in a category
           with a high water loss potential, the maximum evaporation parameter will be automatically adjusted.
        """
        detected_high_water_loss_categories = [cat for cat in self.product.get('categories_tags', [])
                                               if cat in HIGH_WATER_LOSS_CATEGORIES]

        adjusted_coeff = 0
        warning_message = None
        for category in detected_high_water_loss_categories:
            if HIGH_WATER_LOSS_CATEGORIES[category] > adjusted_coeff:
                adjusted_coeff = HIGH_WATER_LOSS_CATEGORIES[category]
                warning_message = f"The category {category} may have an important water loss. " \
                                  f"The maximum evaporation coefficient has been adjusted to {adjusted_coeff}."

        if detected_high_water_loss_categories:
            self.adjusted_maximum_evaporation_coefficient = adjusted_coeff
            self.warnings.append(warning_message)

    def _check_ingredients(self):
        """ Performs some checks on multilevel ingredients. """

        # Remove subingredients from the list of ingredients, keeping them only as nested ingredients
        if OFF_INGREDIENTS_FORMAT == 'flat with rank':
            self.product['ingredients'] = [x for x in self.product['ingredients'] if 'rank' in x]

        # Removing ingredients absent of the OFF taxonomy
        if self.ignore_unknown_ingredients:
            ingredients_remover = UnknownIngredientsRemover()
            ingredients_remover.remove_unknown_ingredients(self.product)
            self.ignored_unknown_ingredients = ingredients_remover.removed_unknown_ingredients

            # If no ingredients are left after the unknown ingredients removal, abort the program
            if 'ingredients' not in self.product:
                raise NoKnownIngredientsError

        # Removing subingredients with no nutrition or impact and without percentages defined
        clear_ingredient_graph(self.product)

        # If no ingredients are left after the ingredient graph cleaning, abort the program
        if 'ingredients' not in self.product:
            raise NoCharacterizedIngredientsError

        # If there are still ingredients but none with impact, abort the program
        if len([ing
                for ing in find_ingredients_graph_leaves(self.product)
                if ing['id'] in ingredients_data
                   and 'impacts' in ingredients_data[ing['id']]]) == 0:
            raise NoCharacterizedIngredientsError

        # If the only ingredient with an impact is en:water, abort the program
        ingredients_with_impacts = [x['id']
                                    for x in self.product['ingredients']
                                    if 'impacts' in ingredients_data.get(x['id'], dict())]
        if ingredients_with_impacts in ([], ['en:water']):
            raise NoKnownIngredientsError

        # Controlling if the subingredients percentages are given in percentage of the parent ingredient (relative)
        # or of the product (absolute)
        define_subingredients_percentage_type(self.product)

        # If ingredients have 'undefined' as percentage type, add a warning.
        nb_undefined_prct_ingredients = 0
        for ingredient in flat_ingredients_list_BFS(self.product):
            if ingredient.get('percent-type') == 'undefined':
                nb_undefined_prct_ingredients += 1
        if nb_undefined_prct_ingredients:
            self.warnings.append(
                f"{nb_undefined_prct_ingredients} compound ingredients whose percentage type is undefined.")

    def reliability_score(self, const_relax_coef, uncharacterized_ingredients_mass_proportion, ):
        """
            Reliability level of the result:
                - 1: Absolutely reliable, no indication of a potential issue in the input data nor in the result
                - 2: Less than 5% of the product ingredients are not in the OFF ingredients taxonomy and less than 5% of
                    the estimated mass of the product is composed of ingredients that are not characterized
                    nutritionally or environmentally and the constraints may have been relaxed by less than 0.05% in
                    order to get a result.
                - 3: Between 5% and 25% of the product ingredients are not in the OFF ingredients taxonomy and between
                    5% and 25% of the estimated mass of the product is composed of ingredients that are not
                    characterized nutritionally or environmentally and the constraints may have been relaxed by less
                    than 0.05% in order to get a result.
                - 4: More than 25% of the ingredients are not in the OFF ingredients taxonomy or more than 25% of the
                    estimated mass of the product is composed of ingredients that are not characterized nutritionally
                    or environmentally, or the constraints has been relaxed by more than 0.05% in order to get a result
                    or the is an important result warning.
        """

        ignored_ingredient_ratio = len(self.ignored_unknown_ingredients) / (len(self.ignored_unknown_ingredients)
                                                                            + len(self.leaf_ingredients))
        # If there is an important warning in the result, it cannot be reliable
        for blocking_warning in RESULTS_WARNINGS_NOT_RELIABLE:
            if any(blocking_warning in x for x in self.warnings):
                return 4

        if const_relax_coef > 0.05:
            return 4

        if (uncharacterized_ingredients_mass_proportion['nutrition'] == 0) \
                and (uncharacterized_ingredients_mass_proportion['impact'] == 0) \
                and (ignored_ingredient_ratio == 0) \
                and (const_relax_coef == 0):
            return 1

        if (uncharacterized_ingredients_mass_proportion['nutrition'] <= 0.05) \
                and (uncharacterized_ingredients_mass_proportion['impact'] <= 0.05) \
                and (ignored_ingredient_ratio <= 0.05) \
                and (const_relax_coef == 0):
            return 2

        if (uncharacterized_ingredients_mass_proportion['nutrition'] <= 0.25) \
                and (uncharacterized_ingredients_mass_proportion['impact'] <= 0.25) \
                and (ignored_ingredient_ratio <= 0.25) \
                and (const_relax_coef <= 0.05):
            return 3

        return 4

    def _check_defined_percentages(self):
        """ Assert that the percentages that might be defined for some ingredients are valid."""

        # Checking that the defined percentages respect these constraints:
        #   - Each ingredient percentage is within its "natural bounds" defined by its rank and the number of products
        #   - The defined percentages does not prevent the total sum to be 100%
        #   - The defined percentages are in decreasing proportion order

        # If the percentage of a top-level ingredient is not in its natural bounds,
        # it is probably a parsing error and should not be used.
        for rank, ingredient in enumerate(self.product['ingredients'], 1):
            if ingredient.get('percent'):
                bounds = natural_bounds(rank, self.nb_ing)
                if not (bounds[0] <= float(ingredient['percent']) <= bounds[1]):
                    self.warnings.append(f"Inconsistencies were found in the defined percentages of the ingredients. "
                                         f"Defined percentage of \"{ingredient['id']}\" ({ingredient['percent']}%)"
                                         f" has not been used.")
                    del ingredient['percent']

        # If the remaining ingredients percentages are not in decreasing order, then at least one ingredient percentage
        # is incorrect but it is not possible to know which one, therefore none can be used
        defined_ingredients_percentages = [float(x['percent'])
                                           for x in self.product['ingredients']
                                           if ('percent' in x)
                                           and (float(x.get('percent', 0)) > 2)]
        if not all(x >= y for x, y in zip(defined_ingredients_percentages, defined_ingredients_percentages[1:])):
            self.use_defined_prct = False

        # If the minimum (resp. maximum) theoretical percentage sum of these ingredients is higher (resp lower)
        # than 100, then at least one ingredient percentage is incorrect but it is not possible to know which one,
        # therefore none can be used
        # Minimum
        minimum_sum = 0
        for rank, ingredient in enumerate(self.product['ingredients'], 1):

            # If the percentage of the ingredient is defined
            if 'percent' in ingredient:
                percentage = float(ingredient['percent'])

            # If the percentage is not defined, it is a least equal to the percentage of the first ingredient with a
            # defined percentage after the current one.
            else:
                next_ingredients_with_prct = [x for x in self.product['ingredients'][rank:] if 'percent' in x]

                if next_ingredients_with_prct:
                    percentage = min(float(next_ingredients_with_prct[0]['percent']),
                                     natural_bounds(rank, self.nb_ing)[0])
                else:
                    percentage = natural_bounds(rank, self.nb_ing)[0]

            # Adding the percentage to the sum
            minimum_sum += percentage

        # If the sum of the minimum percentages is higher than 100, then at least one ingredient percentage is incorrect
        if minimum_sum > 105:
            self.use_defined_prct = False

        maximum_sum = 0
        for rank, ingredient in enumerate(self.product['ingredients'], 1):

            # If the percentage of the ingredient is defined
            if 'percent' in ingredient:
                percentage = float(ingredient['percent'])

            # If the percentage is not defined, it is a most equal to the percentage of the first ingredient with a
            # defined percentage before the current one.
            else:
                next_ingredients_with_prct = [x for x in self.product['ingredients'][:rank - 1] if 'percent' in x]

                if next_ingredients_with_prct:
                    percentage = max(float(next_ingredients_with_prct[-1]['percent']),
                                     natural_bounds(rank, self.nb_ing)[1])
                else:
                    percentage = natural_bounds(rank, self.nb_ing)[1]

            # Adding the percentage to the sum
            maximum_sum += percentage

        # If the sum of the maximum percentages is lower than 100, then at least one ingredient percentage is incorrect
        if maximum_sum < 95:
            self.use_defined_prct = False

        # Removing percentage value from the ingredients if use_defined_prct is False. This is only a security to avoid
        # to accidentally use ingredients defined percentages
        if self.use_defined_prct_arg and not self.use_defined_prct:
            self.warnings.append("Inconsistencies were found in the defined percentages of the ingredients. "
                                 "Defined percentages were not used for estimating the impact.")

            remove_percentage_from_product(self.product)

    def estimate_impacts(self, impact_names, min_run_nb=30, max_run_nb=1000, forced_run_nb=None,
                         confidence_interval_width=0.05, confidence_level=0.95, use_nutritional_info=True,
                         const_relax_coef=0, maximum_evaporation=0.4, total_mass_used=None, min_prct_dist_size=30,
                         dual_gap_type='absolute', dual_gap_limit=0.001, solver_time_limit=60,
                         time_limit_dual_gap_limit=0.01, confidence_weighting=True,
                         use_ingredients_impact_uncertainty=True,
                         quantiles_points=('0.05', '0.25', '0.5', '0.75', '0.95'), distributions_as_result=False,
                         confidence_score_weighting_factor=10):
        """
        Looping by calculating a new random recipe at each loop and stopping when the geometric mean of recipes impacts
        values are stabilized within a given confidence interval.

        The convergence of the values is detected when the arithmetic mean of the log of the impact of the n-th first
        recipes has a normal distribution with a small enough confidence interval. Then the exponential of the
        values is taken to switch back to linear space and obtain the geometric mean of the impacts (geometric mean is
        the arithmetic mean of the log of the values).

        Args:
            impact_names (str or list): Iterable containing impacts names or single impact name.
            min_run_nb (int): Minimum number of run for the Monte-Carlo loop
                A too small number may result in a falsely converging value
            max_run_nb (int): Maximum number of run for the Monte-Carlo loop
            forced_run_nb (int): Used to bypass natural Monte-Carlo stopping criteria and force the number of runs
            confidence_interval_width (float): Width of the confidence interval that will determine the convergence
                detection.
            confidence_level (float): Confidence level of the confidence interval.
            use_nutritional_info (bool): Should nutritional information be used to estimate recipe?
            const_relax_coef (float): Constraints relaxation coefficient. Allows to relax constraints on nutriments,
                water and mass balance to increase chances to get a result.
            maximum_evaporation (float): Upper bound of the evaporation coefficient [0-1[. I.e. maximum proportion of
                ingredients water that can evaporate.
            total_mass_used (float): Total mass of ingredient used in grams, if known.
            min_prct_dist_size (int): Minimum size of the ingredients percentage distribution that will be used to pick
                a proportion for an ingredient. If the distribution (adjusted to the possible value interval) has less
                data, uniform distribution will be used instead.
            dual_gap_type (str): 'absolute' or 'relative'. Determines the precision type of the variable optimization
                by the solver.
            dual_gap_limit (float): Determines the precision of the variable optimization by the solver.
                Relative or absolute according to dual_gap_type.
            solver_time_limit (float): Maximum time for the solver optimization (in seconds).
                Set to None or 0 to set no limit.
            time_limit_dual_gap_limit (float): Accepted precision of the solver in case of time limit hit.
                Relative or absolute according to dual_gap_type.
            use_ingredients_impact_uncertainty (bool): Should ingredients impacts uncertainty data be used?
            confidence_weighting (bool): Should the recipes be weighted by their confidence score (deviation of
             the recipes nutritional composition to the reference product).
            quantiles_points (iterable): List of impacts quantiles cutting points to return in the result.
            distributions_as_result (bool): Should the distributions of the impact, the mean confidence interval and the
                confidence score be added to the result?
            confidence_score_weighting_factor (float): Weighting factor used for the confidence score calculation.
                It corresponds to the weight of the nutritional distance against the absolute difference between the
                 total mass and 100g/100g.

        Returns:
            dict: Dictionary containing the result (the average impacts of all computed recipes) as well as other
            attributes such as the standard deviation of the impacts of all computed recipes, the list of unknown
            ingredients contained in the product, the average mass percentage of unknown ingredients.
        """

        if self.adjusted_maximum_evaporation_coefficient:
            maximum_evaporation = self.adjusted_maximum_evaporation_coefficient

        if ('nutriments' not in self.product) and use_nutritional_info:
            raise AttributeError("The product has no nutriments field. Set use_nutritional_info=False to force a "
                                 "result.")
        if (len(self.product['nutriments']) == 0) and use_nutritional_info:
            raise ValueError("The product nutriments list is empty. Set use_nutritional_info=False to force a result.")

        # Setting variables
        if forced_run_nb is not None:
            min_run_nb = 2
            max_run_nb = forced_run_nb + 1
            confidence_interval_width = 0

        use_nutritional_info = use_nutritional_info if self.use_nutritional_info_override is None \
            else self.use_nutritional_info_override

        # The use of allow_unbalanced_recipe=True is necessary to avoid overestimation of the ingredients total used
        # mass and thus the of the product impacts.
        recipe_creator = RandomRecipeCreator(product=self.product,
                                             use_defined_prct=self.use_defined_prct,
                                             use_nutritional_info=use_nutritional_info,
                                             const_relax_coef=const_relax_coef,
                                             maximum_evaporation=maximum_evaporation,
                                             total_mass_used=total_mass_used,
                                             min_prct_dist_size=min_prct_dist_size,
                                             dual_gap_type=dual_gap_type,
                                             dual_gap_limit=dual_gap_limit,
                                             solver_time_limit=solver_time_limit,
                                             time_limit_dual_gap_limit=time_limit_dual_gap_limit,
                                             allow_unbalanced_recipe=True,
                                             confidence_score_weighting_factor=confidence_score_weighting_factor)

        run = 0
        recipes = []
        impact_names = [impact_names] if type(impact_names) is str else impact_names
        impact_distributions = {impact_name: [] for impact_name in impact_names}
        impact_log_distributions = {impact_name: [] for impact_name in impact_names}
        confidence_score_distribution = []
        total_used_mass_distribution = []
        log_means = {impact_name: [] for impact_name in impact_names}
        mean_confidence_interval_distribution = {impact_name: [] for impact_name in impact_names}
        impact_sign = {impact_name: None for impact_name in impact_names}
        ingredients_impacts_share = {impact: dict() for impact in impact_names}
        convergence_reached = {impact_name: False for impact_name in impact_names}
        impacts_units = dict()
        impacts_quantiles = dict()
        impacts_relative_interquartile = dict()

        # Used to handle impacts that are skipped
        skipped_impacts = []

        def skip_impact(impact_name):
            skipped_impacts.append(impact_name)
            del impact_distributions[impact_name]
            del impact_log_distributions[impact_name]
            del log_means[impact_name]
            del mean_confidence_interval_distribution[impact_name]
            del impact_sign[impact_name]
            del ingredients_impacts_share[impact_name]
            del convergence_reached[impact_name]

        consecutive_null_impact_characterized_ingredients_mass = 0

        # Starting a loop that will end when the convergence is reached for all impacts
        while True:
            # Increment the run counter
            run += 1
            break_main_loop = False

            # Getting a random recipe and adding its impacts to the distributions
            # To ensure there is no possible recipe, wait for several recipe creation errors before to raise an
            #  exception.
            consecutive_recipe_creation_error = 0
            while consecutive_recipe_creation_error < MAX_CONSECUTIVE_RECIPE_CREATION_ERROR:
                try:
                    recipe_100g = recipe_creator.random_recipe()

                    # RandomRecipeCreator.random_recipe() gives a result for 100g of final product.
                    # Adapting the recipe to the product quantity
                    recipe = {k: v * self.product_quantity / 100 for k, v in recipe_100g.items()}

                    break

                except RecipeCreationError:
                    consecutive_recipe_creation_error += 1
                    if VERBOSITY >= 1:
                        print(f'Consecutive recipe creation error: {consecutive_recipe_creation_error}')
                    if consecutive_recipe_creation_error >= MAX_CONSECUTIVE_RECIPE_CREATION_ERROR:
                        raise RecipeCreationError

            # Computing the confidence score of the recipe
            # Compute the confidence score only if nutritional info are used and there is at least one top level
            # category nutriment in common between the computed recipe and the product's nutritional composition
            recipe_nutriments = nutriments_from_recipe(recipe_100g)
            if use_nutritional_info and confidence_weighting and any([f"{x}_100g" in self.product['nutriments']
                                                                      for x in recipe_nutriments
                                                                      if x in TOP_LEVEL_NUTRIMENTS_CATEGORIES]):
                conf_score = confidence_score(nutri=recipe_nutriments,
                                              reference_nutri=self.product['nutriments'],
                                              total_mass=sum([x for x in recipe_100g.values()]),
                                              min_possible_mass=MINIMUM_TOTAL_MASS_FOR_UNBALANCED_RECIPES * 100,
                                              max_possible_mass=100 / (1 - maximum_evaporation))
            else:
                # If the nutritional information is not used, all recipes are supposed to have the same confidence
                # level.
                conf_score = 1

            confidence_score_distribution.append(conf_score)

            # Computing the mass of unknown ingredients and adding it to the distribution
            total_mass = sum([float(x) for x in recipe.values()])
            total_used_mass_distribution.append(total_mass)
            for characterization in 'nutrition', 'impact':
                uncharacterized_ingredients_mass = \
                    sum([float(recipe[x]) / total_mass for x in self.uncharacterized_ingredients_ids[characterization]])
                self.uncharacterized_ingredients_mass_distribution[characterization].append(
                    uncharacterized_ingredients_mass)

            # Adding the recipe to the distribution
            recipes.append(recipe)

            # Computing the impact of the recipe for all impact categories
            for impact_name in impact_names:
                recipe_impact_calculator = RecipeImpactCalculator(recipe, impact_name,
                                                                  use_uncertainty=use_ingredients_impact_uncertainty)
                recipe_impact = recipe_impact_calculator.get_recipe_impact()
                if recipe_impact == 0:
                    # In case of null impact values, the geometric approach is not applicable
                    # TODO: In that case use a linear approach
                    skip_impact(impact_name)
                    self.warnings.append(f'Geometric mean could not be calculated for impact: {impact_name}.\n'
                                         f'This impact has been ignored.')
                    continue

                # In some cases, the recipe impact is None (for ex: if all the ingredients with a characterized impact
                # have a null mass). In that case, rollback this loop run and continue
                if recipe_impact is None:
                    # Rolling back changes
                    run -= 1
                    recipes.pop()
                    confidence_score_distribution.pop()
                    impacts_to_rollback = impact_names[:impact_names.index(impact_name)]
                    for impact_to_rollback in impacts_to_rollback:
                        impact_distributions[impact_to_rollback].pop()
                        impact_log_distributions[impact_to_rollback].pop()

                    consecutive_null_impact_characterized_ingredients_mass += 1

                    if consecutive_null_impact_characterized_ingredients_mass >= \
                            MAX_CONSECUTIVE_NULL_IMPACT_CHARACTERIZED_INGREDIENTS_MASS:
                        raise NoCharacterizedIngredientsError

                    break  # Breaking impact loop

                else:
                    consecutive_null_impact_characterized_ingredients_mass = 0

                recipe_impact_log = math.log(abs(recipe_impact))  # Switching to log space
                impact_distributions[impact_name].append(recipe_impact)
                impact_log_distributions[impact_name].append(recipe_impact_log)
                # Getting the sign of the recipe impact.
                # If it has changed from the previous loop, then a geometric mean cannot be computed
                # (both positive and negative values to aggregate)
                if impact_sign[impact_name] is None:
                    impact_sign[impact_name] = recipe_impact / abs(recipe_impact)
                elif impact_sign[impact_name] != recipe_impact / abs(recipe_impact):
                    # If there are both positive and negative values, do not calculate this impact and add a warning
                    # TODO: In that case, instead of not calculating the impact, use a linear approach, by considering
                    #  the distribution of the impacts normal and looking for the impact convergence (not the impact
                    #  logs).
                    skip_impact(impact_name)
                    self.warnings.append(f'Geometric mean could not be calculated for impact: {impact_name}.\n'
                                         f'This impact has been ignored.')
                    continue

                # Computing the average share of impact due to each ingredient
                for ingredient in [x for x in recipe if x not in self.ignored_unknown_ingredients]:
                    try:
                        ingredient_impact_share = recipe_impact_calculator.get_ingredient_impact_share(ingredient)

                        if impact_name not in impacts_units:
                            impacts_units[impact_name] = AGRIBALYSE_IMPACT_UNITS[impact_name]

                        if run == 1:
                            ingredients_impacts_share[impact_name][ingredient] = ingredient_impact_share
                        else:
                            if ingredient_impact_share is not None:
                                # Iterative weighted arithmetic mean of the ingredient impact share
                                ingredients_impacts_share[impact_name][ingredient] = \
                                    ((sum(confidence_score_distribution[:- 1]) * ingredients_impacts_share[impact_name][
                                        ingredient]) +
                                     (confidence_score_distribution[-1] * ingredient_impact_share)) / sum(
                                        confidence_score_distribution)

                    except KeyError:
                        ingredients_impacts_share[impact_name][ingredient] = None

                # Adding the weighted mean of the impacts logs distribution to the list of means
                log_means[impact_name].append(float(sms.DescrStatsW(data=impact_log_distributions[impact_name],
                                                                    weights=confidence_score_distribution
                                                                    if confidence_weighting
                                                                    else None).mean))

                if run >= min_run_nb:
                    # Estimating confidence interval using a Student distribution as the variance is unknown
                    confidence_interval = sms.DescrStatsW(log_means[impact_name]) \
                        .tconfint_mean(alpha=1 - confidence_level)

                    # Converting the confidence interval back to linear space
                    confidence_interval = math.exp(confidence_interval[0]), math.exp(confidence_interval[1])
                    mean_confidence_interval_distribution[impact_name].append((confidence_interval[0],
                                                                               confidence_interval[1]))

                    if ((confidence_interval[1] - confidence_interval[0]) /
                        mean([confidence_interval[1], confidence_interval[0]])) < confidence_interval_width:
                        convergence_reached[impact_name] = True

                    # If the convergence has been reached for all impacts, ends the main while loop
                    if all(convergence_reached.values()):
                        break_main_loop = True
                        # break

                if run >= max_run_nb:
                    break_main_loop = True
                    for impact_name_conv, conv in convergence_reached.items():
                        if not conv:
                            self.warnings.append(f'Maximum run number has been reached before convergence '
                                                 f'of impact "{impact_name_conv}"')
                    break

                if run == forced_run_nb:
                    break_main_loop = True
                    break

            # Once the loop is over, impacts_names can be edited
            impact_names = [x for x in impact_names if x not in skipped_impacts]

            if break_main_loop:
                break

        # Compute and return the result if no exception are raised
        uncharacterized_ingredients_mass_proportion = dict()
        for characterization in 'nutrition', 'impact':
            uncharacterized_ingredients_mass_proportion[characterization] = \
                mean(self.uncharacterized_ingredients_mass_distribution[characterization])
            if uncharacterized_ingredients_mass_proportion[characterization] \
                    > UNCHARACTERIZED_INGREDIENTS_MASS_WARNING_THRESHOLD:
                self.warnings.append(f"The estimated mass of {characterization} uncharacterized"
                                     f" ingredients in the product is high: "
                                     f"{uncharacterized_ingredients_mass_proportion[characterization]:.0%}")

        if self.ignored_unknown_ingredients:
            self.warnings.append(f"{len(self.ignored_unknown_ingredients)} ingredients have been ignored because they "
                                 "are absent of OFF ingredients taxonomy.")

        # Exponential used to switch back to linear space as the geometric mean is the exponential of the arithmetic
        #  mean of the logs
        impacts_geom_means = {
            impact: impact_sign[impact] * math.exp(
                sms.DescrStatsW(data=impact_log_distributions[impact],
                                weights=confidence_score_distribution
                                if confidence_weighting
                                else None).mean)
            for impact in
            impact_distributions}

        # The geometric stdev is the exponential of the square root of the variance of the log of the data
        impacts_geom_stdevs = {impact: math.exp(math.sqrt(sms.DescrStatsW(data=impact_log_distributions[impact],
                                                                          weights=confidence_score_distribution
                                                                          if confidence_weighting
                                                                          else None).var))
                               for impact in
                               impact_distributions}

        # Computing the weighted quantiles of the impacts
        for impact_name in impact_names:
            quantiles = sms.DescrStatsW(data=impact_distributions[impact_name],
                                        weights=confidence_score_distribution
                                        if confidence_weighting
                                        else None).quantile([float(x) for x in quantiles_points])

            impacts_quantiles[impact_name] = {str(quantiles_points[index]): value
                                              for index, value in enumerate(quantiles)}

            # Relative interquartile
            if '0.25' in quantiles:
                first_quartile = impacts_quantiles[impact_name]['0.25']
            else:
                first_quartile = float(sms.DescrStatsW(data=impact_distributions[impact_name],
                                                       weights=confidence_score_distribution
                                                       if confidence_weighting
                                                       else None).quantile(0.25))
            if '0.75' in quantiles:
                third_quartile = impacts_quantiles[impact_name]['0.75']
            else:
                third_quartile = float(sms.DescrStatsW(data=impact_distributions[impact_name],
                                                       weights=confidence_score_distribution
                                                       if confidence_weighting
                                                       else None).quantile(0.75))
            if '0.5' in quantiles:
                median = impacts_quantiles[impact_name]['0.5']
            else:
                median = float(sms.DescrStatsW(data=impact_distributions[impact_name],
                                               weights=confidence_score_distribution
                                               if confidence_weighting
                                               else None).quantile(0.5))

            impacts_relative_interquartile[impact_name] = (third_quartile - first_quartile) / median

            if impacts_relative_interquartile[impact_name] > IMPACT_RELATIVE_INTERQUARTILE_WARNING_THRESHOLD:
                self.warnings.append(
                    f"The impact relative interquartile is high for {impact_name}"
                    f" ({impacts_relative_interquartile[impact_name]:.0%})")

        # Computing the average total used mass
        average_total_used_mass = sms.DescrStatsW(data=total_used_mass_distribution,
                                                  weights=confidence_score_distribution
                                                  if confidence_weighting
                                                  else None).mean

        # Computing the weighted average mass share of each ingredient
        # Poorly optimized...
        average_mass_shares = dict()
        for ingredient in recipes[0]:
            mass_shares = [x[ingredient] / sum(x.values()) for x in recipes]
            average_mass_shares[ingredient] = sms.DescrStatsW(data=mass_shares,
                                                              weights=confidence_score_distribution
                                                              if confidence_weighting
                                                              else None).mean

        # Retrieving the databases entries related to each ingredient
        data_sources = dict()
        for ingredient in flat_ingredients_list_BFS(self.product):
            if (ingredient['id'] not in self.ignored_unknown_ingredients) and (ingredient['id'] in ingredients_data):
                ingredient_data = ingredients_data[ingredient['id']]
                ingredient_data_sources = dict()

                if 'environmental_impact_data_sources' in ingredient_data:
                    ingredient_data_sources['environmental_impact'] = ingredient_data[
                        'environmental_impact_data_sources']

                if 'nutritional_data_sources' in ingredient_data:
                    ingredient_data_sources['nutrition'] = ingredient_data['nutritional_data_sources']

                if len(ingredient_data_sources) > 0:
                    data_sources[ingredient['id']] = ingredient_data_sources

        result = {'impacts_geom_means': impacts_geom_means,
                  'impacts_geom_stdevs': impacts_geom_stdevs,
                  'impacts_quantiles': impacts_quantiles,
                  'impacts_relative_interquartile': impacts_relative_interquartile,
                  'ingredients_impacts_share': ingredients_impacts_share,
                  'ingredients_mass_share': average_mass_shares,
                  'impacts_units': impacts_units,
                  'product_quantity': self.product_quantity,
                  'const_relax_coef': const_relax_coef,
                  'warnings': self.warnings,
                  'reliability': self.reliability_score(
                      const_relax_coef=const_relax_coef,
                      uncharacterized_ingredients_mass_proportion=uncharacterized_ingredients_mass_proportion),
                  'ignored_unknown_ingredients': self.ignored_unknown_ingredients,
                  'uncharacterized_ingredients': self.uncharacterized_ingredients_ids,
                  'uncharacterized_ingredients_ratio': self.uncharacterized_ingredients_ratio,
                  'uncharacterized_ingredients_mass_proportion': uncharacterized_ingredients_mass_proportion,
                  'number_of_runs': run,
                  'number_of_ingredients': len(self.leaf_ingredients),
                  'average_total_used_mass': average_total_used_mass,
                  'calculation_time': time.time() - self.start_time,
                  'data_sources': data_sources
                  }

        if distributions_as_result:
            result.update({'impact_distributions': impact_distributions,
                           'mean_confidence_interval_distribution': mean_confidence_interval_distribution,
                           'confidence_score_distribution': confidence_score_distribution,
                           'recipes': recipes,
                           'total_used_mass_distribution': total_used_mass_distribution})

        return result


def estimate_impacts(product, impact_names, quantity=100, ignore_unknown_ingredients=True, min_run_nb=30,
                     max_run_nb=1000, forced_run_nb=None, confidence_interval_width=0.05, confidence_level=0.95,
                     use_nutritional_info=True, const_relax_coef=0, use_defined_prct=True, maximum_evaporation=0.4,
                     total_mass_used=None, min_prct_dist_size=30, dual_gap_type='absolute', dual_gap_limit=0.001,
                     solver_time_limit=60, time_limit_dual_gap_limit=0.01, confidence_weighting=True,
                     use_ingredients_impact_uncertainty=True, quantiles_points=('0.05', '0.25', '0.5', '0.75', '0.95'),
                     distributions_as_result=False, confidence_score_weighting_factor=10, safe_mode=True):
    """
        Wrapper for impact estimation that will maximise the chances of getting a result by running the program with
        more permissive parameters in case of error.

        Args:
            safe_mode (bool): If set to True, the constraints will be progressively relaxed in order to get a result.
    """

    impact_estimator_kwargs = dict(product=product,
                                   quantity=quantity,
                                   ignore_unknown_ingredients=ignore_unknown_ingredients,
                                   use_defined_prct=use_defined_prct)

    impact_estimation_method_kwargs = dict(impact_names=impact_names,
                                           min_run_nb=min_run_nb,
                                           max_run_nb=max_run_nb,
                                           forced_run_nb=forced_run_nb,
                                           confidence_interval_width=confidence_interval_width,
                                           confidence_level=confidence_level,
                                           use_nutritional_info=use_nutritional_info,
                                           const_relax_coef=const_relax_coef,
                                           maximum_evaporation=maximum_evaporation,
                                           total_mass_used=total_mass_used,
                                           min_prct_dist_size=min_prct_dist_size,
                                           dual_gap_type=dual_gap_type,
                                           dual_gap_limit=dual_gap_limit,
                                           solver_time_limit=solver_time_limit,
                                           time_limit_dual_gap_limit=time_limit_dual_gap_limit,
                                           confidence_weighting=confidence_weighting,
                                           use_ingredients_impact_uncertainty=use_ingredients_impact_uncertainty,
                                           quantiles_points=quantiles_points,
                                           distributions_as_result=distributions_as_result,
                                           confidence_score_weighting_factor=confidence_score_weighting_factor)

    # First attempt for getting a result with provided kwargs
    try:
        impact_estimator = ImpactEstimator(**impact_estimator_kwargs)
        return impact_estimator.estimate_impacts(**impact_estimation_method_kwargs)

    except (RecipeCreationError, SolverTimeoutError) as original_exception:

        # If the safe mode is not enabled, raise the exception, else retry with relaxed constraints
        if not safe_mode:
            raise original_exception

        # Preparing kwargs to loop on, with decreasing constraints
        constraints_levels = [
            {'use_defined_prct': True, 'const_relax_coef': 0.01},
            {'use_defined_prct': True, 'const_relax_coef': 0.05},
            {'use_defined_prct': True, 'const_relax_coef': 0.1},
            {'use_defined_prct': True, 'const_relax_coef': 0.2},
            {'use_defined_prct': True, 'const_relax_coef': 0.3},
            {'use_defined_prct': True, 'const_relax_coef': 0.4},
            {'use_defined_prct': True, 'const_relax_coef': 0.5},
            {'use_defined_prct': True, 'const_relax_coef': 0.6},
            {'use_defined_prct': True, 'const_relax_coef': 0.7},
            {'use_defined_prct': True, 'const_relax_coef': 0.8},
            {'use_defined_prct': True, 'const_relax_coef': 0.9},
            {'use_defined_prct': True, 'const_relax_coef': 1},
            {'use_defined_prct': False, 'const_relax_coef': 0.01},
            {'use_defined_prct': False, 'const_relax_coef': 0.05},
            {'use_defined_prct': False, 'const_relax_coef': 0.1},
            {'use_defined_prct': False, 'const_relax_coef': 0.2},
            {'use_defined_prct': False, 'const_relax_coef': 0.3},
            {'use_defined_prct': False, 'const_relax_coef': 0.4},
            {'use_defined_prct': False, 'const_relax_coef': 0.5},
            {'use_defined_prct': False, 'const_relax_coef': 0.6},
            {'use_defined_prct': False, 'const_relax_coef': 0.7},
            {'use_defined_prct': False, 'const_relax_coef': 0.8},
            {'use_defined_prct': False, 'const_relax_coef': 0.9},
            {'use_defined_prct': False, 'const_relax_coef': 1}
        ]

        for constraints_level in constraints_levels:
            new_impact_estimator_kwargs = copy.deepcopy(impact_estimator_kwargs)
            new_impact_estimation_method_kwargs = copy.deepcopy(impact_estimation_method_kwargs)
            added_warnings = []

            for kwarg, value in constraints_level.items():
                # Avoid to use a more restrictive parameter than the kwargs provided
                if kwarg == 'use_defined_prct':
                    original_kwarg_value = impact_estimator_kwargs.get(kwarg, True)
                    new_value = value and original_kwarg_value
                    new_impact_estimator_kwargs['use_defined_prct'] = new_value
                elif kwarg == 'const_relax_coef':
                    original_kwarg_value = impact_estimation_method_kwargs.get(kwarg, 0)
                    new_value = max(value, original_kwarg_value)
                    new_impact_estimation_method_kwargs['const_relax_coef'] = new_value
                else:
                    raise Exception('Not implemented.')

                # Add the change of parameter in the warnings
                if new_value != original_kwarg_value:
                    added_warnings.append(
                        f"Parameter {kwarg} has been set to {new_value} in order to get a result.")

            try:
                impact_estimator = ImpactEstimator(**new_impact_estimator_kwargs)
                result = impact_estimator.estimate_impacts(**new_impact_estimation_method_kwargs)
                result['warnings'] += added_warnings
                return result
            except (RecipeCreationError, SolverTimeoutError):
                pass

        # If no result has been returned with more permissive parameters, raise the original error
        raise original_exception


def estimate_impacts_safe(product, impact_names, **kwargs):
    warnings.warn(message="This function is deprecated. Use estimate_impacts() with safe_mode=True instead.",
                  category=Warning)

    return estimate_impacts(product=product, impact_names=impact_names, **kwargs)
