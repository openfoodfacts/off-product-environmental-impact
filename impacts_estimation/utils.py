""" Functions used by the environmental impact estimation program """

import copy
import numpy as np
from math import sqrt
import random

from impacts_estimation.vars import NUTRIMENTS_CATEGORIES, TOP_LEVEL_NUTRIMENTS_CATEGORIES, IMPACT_MASS_UNIT
from data import ingredients_data, off_taxonomy


def impact_from_recipe(recipe, impact_name, use_uncertainty=True):
    """
    Calculate the environmental impact from a product recipe.

    Args:
        recipe (dict): Dict containing ingredients as keys and masses in grams as values
        impact_name (str): Name of the impact as in the ingredients data
        use_uncertainty (bool): Should the ingredients uncertainty data be used to pick a randomized impact value?
            If True, the result may vary from one call to another.

    Warning:
        Any ingredients whose impact is unknown will be considered to have the average impact of the product.

    Returns:
        float: Impact of the product
    """

    result = 0
    known_ingredients_mass = 0
    total_mass = sum([float(x) for x in recipe.values()])

    # Looping on all ingredients that has a value for the considered impact
    for ingredient in recipe:
        if (ingredient in ingredients_data) \
                and ('impacts' in ingredients_data[ingredient]) \
                and (impact_name in ingredients_data[ingredient]['impacts']):

            # Adding the ingredient the the known ingredients mass
            known_ingredients_mass += float(recipe[ingredient])

            # Getting the ingredient impact. If the ingredient has no uncertainty parameters or use_uncertainty is set
            # to False, simply use the default value. Else pick a value using the uncertainty parameters.
            ingredient_impact_data = ingredients_data[ingredient]['impacts'][impact_name]
            rng = np.random.default_rng()
            if ('uncertainty_distributions' not in ingredient_impact_data) or (not use_uncertainty):
                ingredient_impact = ingredient_impact_data['amount']
            else:
                # Pick a random uncertainty distribution
                uncertainty_distribution = random.choice(ingredient_impact_data['uncertainty_distributions'])
                if uncertainty_distribution['distribution'] == 'normal':
                    ingredient_impact = rng.normal(uncertainty_distribution['mean'],
                                                   uncertainty_distribution['standard deviation'])
                elif uncertainty_distribution['distribution'] == 'lognormal':
                    if uncertainty_distribution['geometric mean'] >= 0:
                        # Numpy requires the mean and std of the underlying normal distribution, which are the logs of
                        # the mean and std of the lognormal distribution.
                        ingredient_impact = rng.lognormal(np.log(uncertainty_distribution['geometric mean']),
                                                          np.log(uncertainty_distribution['geometric standard deviation']))
                    # If the geometric mean is negative, then simply take the opposite of the value generated
                    # with the opposite of the geometric mean
                    if uncertainty_distribution['geometric mean'] < 0:
                        ingredient_impact = - rng.lognormal(np.log(-uncertainty_distribution['geometric mean']),
                                                            np.log(uncertainty_distribution['geometric standard deviation']))
                elif uncertainty_distribution['distribution'] == 'triangular':
                    ingredient_impact = rng.triangular(uncertainty_distribution['minimum'],
                                                       uncertainty_distribution['mode'],
                                                       uncertainty_distribution['maximum'])
                elif uncertainty_distribution['distribution'] == 'uniform':
                    ingredient_impact = rng.uniform(uncertainty_distribution['minimum'],
                                                    uncertainty_distribution['maximum'])
                else:
                    raise ValueError(f"Unknown distribution type {uncertainty_distribution['distribution']}"
                                     f" for ingredient {ingredient}")

            # Adding the impact to the result
            result += float(recipe[ingredient]) * ingredient_impact / IMPACT_MASS_UNIT

    if known_ingredients_mass == 0:
        return None
    else:
        # Inflating the impact of the known ingredients to the impact of the total mass of these ingredients
        return result * total_mass / known_ingredients_mass


def nutriments_from_recipe(recipe):
    """
    Return the nutriments content of a product recipe by a weighted sum of the ingredients masses and reference
    nutriment contents.

    Args:
        recipe (dict): Dict containing ingredients as keys and masses in grams as values

    Warning:
        Any ingredients whose nutriment content is unknown will be considered to have the average nutriment content
        of the product.

    Returns:
        dict: Dictionary with nutriments as keys and nutriment contents as values
    """

    result = dict()
    total_mass = sum([float(x) for x in recipe.values()])

    for nutriment in NUTRIMENTS_CATEGORIES:
        known_ingredients_mass = 0
        result[nutriment] = 0
        for ingredient in recipe:
            if (ingredient in ingredients_data) and (nutriment in ingredients_data[ingredient].get('nutriments', [])):
                known_ingredients_mass += float(recipe[ingredient])
                result[nutriment] += float(recipe[ingredient]) * \
                                     ingredients_data[ingredient]['nutriments'][nutriment]['value'] \
                                     / 100  # Ingredients nutriment contents are given per 100g

        if known_ingredients_mass == 0:
            del result[nutriment]
        # Inflating the nutriment content of the known ingredients to the nutriment content of the total mass of these
        # ingredients
        else:
            result[nutriment] = result[nutriment] * total_mass / known_ingredients_mass

    return result


def confidence_score(nutri, reference_nutri, total_mass):
    """
    Calculate the confidence score of a nutritional composition using the euclidean distance between the reference
    nutritional composition and the assessed nutritional composition in the space of all considered nutriments
    contents and the total mass of ingredients used. The closer the nutritional composition is from the reference, the
    higher the confidence score is. The lower the total mass of ingredients is, the higher the confidence score is.

    A score of 1 correspond to the lowest match between compositions. The higher the score, the better the match.

    Args:
        nutri (dict): Nutritional composition to evaluate.
        reference_nutri (dict): Nutritional composition of the reference product.
        total_mass (float): Total mass of ingredients used in g.

    Returns:
        float: Confidence score
    """
    assert float(total_mass) >= 99.99  # Not 100 to avoid precision issues
    total_mass = total_mass / 100

    squared_differences = []
    n = 0
    for nutriment in nutri:
        if nutriment in TOP_LEVEL_NUTRIMENTS_CATEGORIES:
            if f"{nutriment}_100g" in reference_nutri:
                n += 1  # Incrementing the number of considered dimensions (nutriments)
                squared_difference = ((float(reference_nutri[f"{nutriment}_100g"]) / 100) -
                                      (float(nutri[nutriment]) / 100)) ** 2

                if squared_difference > 1:
                    raise ValueError("The squared difference cannot be superior to 1.")

                squared_differences.append(squared_difference)

    # The distance in the n-dimensional space is the square root of the sum of the squared differences
    distance = sqrt(sum(squared_differences))

    # Returning the inverse of the distance normalized by the biggest possible distance between two compositions in the
    #  n-dimensional space (sqrt(n))
    return sqrt(n) / (distance * total_mass)


def natural_bounds(rank, nb_ingredients):
    """
    Computes the upper and lower bounds of the proportion of an ingredient depending on its rank and the number of
    ingredients in the product given that they are in decreasing proportion order.

    Examples:
        >>> natural_bounds(2, 4)
        (0.0, 50.0)
        >>> natural_bounds(1, 5)
        (20.0, 100.0)

    Args:
        rank (int): Rank of the ingredient in the list
        nb_ingredients (int): Number of ingredients in the product

    Returns:
        tuple: Lower and upper bounds of the proportion of the ingredient
    """
    if rank == 1:
        return 100 / nb_ingredients, 100.0
    else:
        return .0, 100 / rank


def nutritional_error_margin(nutriment, value):
    """
    Returns the error margin of a product's nutriment according to EU directives

    Args:
        nutriment (str): Nutriment considered
        value (float): Given product content of the considered nutriment

    Returns:
        dict: Dictionary containing absolute and relative margins (only one of which is different from 0)

    Examples:
        >>>nutritional_error_margin('proteins', 0.05)
        {'absolute': 0.02, 'relative': 0}
        >>>nutritional_error_margin('proteins', 0.3)
        {'absolute': 0, 'relative': 0.2}
    """

    value = float(value)
    assert 0 <= value <= 1

    if nutriment.lower() in ('proteins', 'carbohydrates', 'sugars', 'fiber'):
        if 0 <= value < 0.1:
            return {'absolute': 0.02, 'relative': 0}
        elif 0.1 <= value < 0.4:
            return {'absolute': 0, 'relative': 0.2}
        elif 0.4 <= value <= 1:
            return {'absolute': 0.08, 'relative': 0}

    elif nutriment.lower() == 'fat':
        if 0 <= value < 0.1:
            return {'absolute': 0.015, 'relative': 0}
        elif 0.1 <= value < 0.4:
            return {'absolute': 0, 'relative': 0.2}
        elif 0.4 <= value <= 1:
            return {'absolute': 0.08, 'relative': 0}

    elif nutriment.lower() == 'saturated-fat':
        if 0 <= value < 0.04:
            return {'absolute': 0.008, 'relative': 0}
        elif 0.04 <= value <= 1:
            return {'absolute': 0, 'relative': 0.2}

    elif nutriment.lower() == 'salt':
        if 0 <= value < 0.0125:
            return {'absolute': 0.00375, 'relative': 0}
        elif 0.0125 <= value <= 1:
            return {'absolute': 0, 'relative': 0.2}

    else:
        raise ValueError('The nutriment is not recognized.')


def clear_ingredient_graph(product):
    """
    Recursive function to search the ingredients graph and remove subingredients if all subingredients of a same
    ingredient are uncharacterized

    Args:
        product (dict): Dict corresponding to a product or a compound ingredient.
    """
    ingredients = product['ingredients']
    for ingredient in ingredients:
        # If the ingredient has subingredients, recursively call the function
        if 'ingredients' in ingredient:
            clear_ingredient_graph(ingredient)

    # If no subingredients are known, have known subingredients or defined percentage, delete them all
    if len([x for x in ingredients
            if (x['id'] in ingredients_data)
               or ('ingredients' in x)
               or ('percent' in x)]
           ) == 0:
        del product['ingredients']


def minimum_percentage_sum(ingredients):
    """
    Computes the minimum sum of ingredients percentages for ingredients given in decreasing percentage order, even if
    some ingredients does not have a percentage.

    Notes:
        This is useful to estimate if subingredients percentages are defined in percentage of their parent ingredient
        or in percentage of the total product.

    Args:
        ingredients (list): List of dicts corresponding to the ingredients

    Returns:
        float: Minimum value of the sum of all ingredients percentages.
    """

    # Looping from least present ingredient to most present
    ingredients = copy.deepcopy(ingredients)
    ingredients.reverse()
    minimum_sum = 0
    minimum_percentage = 0
    for ingredient in ingredients:
        if 'percent' in ingredient:
            minimum_percentage = float(ingredient['percent'])

        minimum_sum += minimum_percentage

    return minimum_sum


def maximum_percentage_sum(ingredients):
    """
    Computes the maximum sum of ingredients percentages for ingredients given in decreasing percentage order, even if
    some ingredients does not have a percentage.

    Notes:
        This is useful to estimate if subingredients percentages are defined in percentage of their parent ingredient
        or in percentage of the total product.

    Args:
        ingredients (list): List of dicts corresponding to the ingredients

    Returns:
        float: Maximum value of the sum of all ingredients percentages.
    """

    maximum_sum = 0
    maximum_percentage = 100
    for ingredient in ingredients:
        if 'percent' in ingredient:
            maximum_percentage = float(ingredient['percent'])

        maximum_sum += maximum_percentage

    return maximum_sum


def define_subingredients_percentage_type(product):
    """
    Recursive function to search the ingredients graph and define if the subingredients percentages are defined as
    percentage of their parent ingredient or the whole product.

    Args:
        product (dict): Dict corresponding to a product or a compound ingredient.
    """
    for rank, ingredient in enumerate(product['ingredients'], 1):
        if ingredient.get('ingredients'):

            # Recursive call for each subingredients:
            define_subingredients_percentage_type(ingredient)

            parent_percentage = True
            product_percentage = True
            # If the maximum sum of the subingredients percentages is lower than 100, then the percentages cannot
            # be given in percentage of the parent
            if maximum_percentage_sum(ingredient['ingredients']) < 100:
                parent_percentage = False

            # If the minimum sum of the subingredients percentages is higher than the parent ingredient percentage
            # or its natural upper bound (if the parent has no percentage), then the subingredients percentages
            # cannot be given in percentage of the product
            parent_ingredient_percentage = min(float(ingredient.get('percent', 100)),
                                               natural_bounds(rank, len(product['ingredients']))[1])

            if minimum_percentage_sum(ingredient['ingredients']) > parent_ingredient_percentage:
                product_percentage = False
            if parent_percentage and not product_percentage:
                ingredient['percent-type'] = 'parent'
            elif product_percentage and not parent_percentage:
                ingredient['percent-type'] = 'product'
            else:
                ingredient['percent-type'] = 'undefined'


def flat_ingredients_list(product):
    """
    Recursive function to search the ingredients graph and return it as a flat list of all nodes.

    Args:
        product (dict): Dict corresponding to a product or a compound ingredient.

    Returns:
        list: List containing all the ingredients graph nodes.
    """
    nodes = []
    if 'ingredients' in product:
        ingredients = copy.deepcopy(product['ingredients'])  # Deepcopy to avoid deleting the graph structure
        nodes += ingredients

        for ingredient in ingredients:
            nodes += flat_ingredients_list(ingredient)

            if 'ingredients' in ingredient:
                del ingredient['ingredients']

    return nodes


def find_ingredients_graph_leaves(product):
    """
    Recursive function to search the ingredients graph and find its leaves.

    Args:
        product (dict): Dict corresponding to a product or a compound ingredient.

    Returns:
        list: List containing the ingredients graph leaves.
    """

    if 'ingredients' in product:
        leaves = []
        for ingredient in product['ingredients']:
            subleaves = find_ingredients_graph_leaves(ingredient)

            if type(subleaves) == list:
                leaves += subleaves
            else:
                leaves.append(subleaves)

        return leaves

    else:
        return product


def individualize_ingredients(product, previous_ingredients_ids=None):
    """
    Process an ingredient list in place to ensure that they all have a different id.

    Args:
        product (dict): Dict corresponding to a product, containing a list of ingredients, may contain compound
            ingredients
        previous_ingredients_ids (list): List containing ingredients ids. Needed only for recursive call

    Examples:
        >>> product = {'ingredients': [{'id': 'A'}, {'id': 'B', 'ingredients': [{'id': 'A'}]}, {'id': 'B'}]}
        >>> individualize_ingredients(product)
        >>> print(product)
        {'ingredients': [{'id': 'A'}, {'id': 'B', 'ingredients': [{'id': 'A*'}]}, {'id': 'B*'}]}
    """
    ingredients_ids = previous_ingredients_ids or []

    for ingredient in product['ingredients']:
        # Appending an asterisk to the id as long as the id already exists
        while ingredient['id'] in ingredients_ids:
            ingredient['id'] += '*'

        ingredients_ids.append(ingredient['id'])

        if 'ingredients' in ingredient:
            individualize_ingredients(ingredient, previous_ingredients_ids=ingredients_ids)


def original_id(individualized_id):
    """
    Gets the original id of an ingredient that has been transformed by individualize_ingredients()

    Args:
        individualized_id (str):

    Returns:
        str:

    Examples:
        >>> original_id('en:water**')
        'en:water'
        >>> original_id('en:sugar')
        'en:sugar'
    """

    return individualized_id.strip('*')


class UnknownIngredientsRemover:
    def __init__(self):
        self.removed_unknown_ingredients = []

    def remove_unknown_ingredients(self, product):
        """
            Recursive function to remove ingredients if they are not in the OFF taxonomy or if they do not have a
            defined percentage or valid subingredients.
        """

        if 'ingredients' in product:

            # Recursive call on each subingredients
            for ingredient in product['ingredients']:
                self.remove_unknown_ingredients(ingredient)

            # Creating an iteration copy
            iter_ingredients = copy.deepcopy(product['ingredients'])

            # Removing ingredients from the list if they do not have sub-ingredients,
            # nor defined percentage and are not in the OFF taxonomy
            for ingredient in iter_ingredients:
                if ('ingredients' not in ingredient) \
                        and ('percent' not in ingredient) \
                        and ingredient['id'] not in off_taxonomy:
                    product['ingredients'].remove(ingredient)
                    self.removed_unknown_ingredients.append(ingredient['id'])

            # Removing the 'ingredients' key if empty
            if len(product['ingredients']) == 0:
                del product['ingredients']


def remove_percentage_from_product(product):
    """
    Removes the defined percentage of ingredients.

    Args:
        product (dict):
    """

    for ingredient in product['ingredients']:
        if 'percent' in ingredient:
            del ingredient['percent']

        if 'ingredients' in ingredient:
            remove_percentage_from_product(ingredient)


def weighted_geometric_mean(values, weights):
    """
    Returns the weighted geometric mean of values.

    Args:
        values (iterable):
        weights (iterable):

    Returns:
        float:
    """

    assert len(values) == len(weights)
    return np.exp(sum([weights[i] * np.log(values[i]) for i in range(len(values))]) /
                  sum([weights[i] for i in range(len(values))]))
