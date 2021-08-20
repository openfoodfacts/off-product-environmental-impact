""" Functions used by the environmental impact estimation program """

import copy
import numpy as np
from math import sqrt

from impacts_estimation.vars import NUTRIMENTS_CATEGORIES, TOP_LEVEL_NUTRIMENTS_CATEGORIES, \
    AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR, AGRIBALYSE_IMPACT_CATEGORIES_FR
from data import ingredients_data, off_taxonomy


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


def confidence_score(nutri, reference_nutri, total_mass, min_possible_mass, max_possible_mass, weighting_factor=10,
                     reference_mass=100):
    """
    Calculate the confidence score of a nutritional composition using the euclidean distance between the reference
    nutritional composition and the assessed nutritional composition in the space of all considered nutriments
    contents and the total mass of ingredients used. The closer the nutritional composition is from the reference, the
    higher the confidence score is. The nearest of 100g/100g the total mass of ingredients is, the higher the confidence
     score is.

    The score is defined as the inverse of the sum of the nutritional distance and the absolute difference between the
    total mass and 100g/100g weighted by a weighting factor.

    Args:
        nutri (dict): Nutritional composition to evaluate.
        reference_nutri (dict): Nutritional composition of the reference product.
        total_mass (float): Total mass of ingredients used in g.
        min_possible_mass (float): Minimum possible total ingredient mass for a product in g
        max_possible_mass (float): Maximum possible total ingredient mass for a product in g
        weighting_factor (float): Weight of the nutritional distance against the absolute difference between
         the total mass and 100g/100g.
        reference_mass (float): Mass for which the nutritional compositions are expressed (in g).

    Returns:
        float: Confidence score
    """
    assert round(min_possible_mass) <= round(total_mass) <= round(max_possible_mass)

    total_mass = total_mass / reference_mass
    min_possible_mass = min_possible_mass / reference_mass
    max_possible_mass = max_possible_mass / reference_mass

    # Removing "_100g" from reference_nutri keys
    reference_nutri = {k.replace('_100g', ''): v for k, v in reference_nutri.items()}

    # Calculating nutritional distance
    squared_differences = []
    n = 0
    for nutriment in nutri:
        if nutriment in TOP_LEVEL_NUTRIMENTS_CATEGORIES:
            if nutriment in reference_nutri:
                n += 1  # Incrementing the number of considered dimensions (nutriments)
                difference = (float(reference_nutri[nutriment]) / reference_mass) \
                             - (float(nutri[nutriment]) / reference_mass)

                squared_difference = round(difference ** 2, 6)

                # Setting a minimal squared difference to avoid extremely high confidence score values in case of very
                # similar nutritional compositions
                squared_difference = max(squared_difference, 0.0000001)

                if squared_difference > 1:
                    raise ValueError("The squared difference cannot be superior to 1.")

                squared_differences.append(squared_difference)

    # The distance in the n-dimensional space is the square root of the sum of the squared differences
    nutri_distance = sqrt(sum(squared_differences))

    # Normalizing by the maximum possible distance sqrt(2)
    normalized_nutri_distance = nutri_distance / sqrt(2)

    # Calculating total mass likelihood coefficient
    if total_mass < 1:
        mass_diff = (1 - total_mass) / (1 - min_possible_mass)
    else:
        mass_diff = (total_mass - 1) / (max_possible_mass - 1)

    return 1 / ((normalized_nutri_distance * weighting_factor) + mass_diff)


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

            if not any('percent' in x for x in ingredient['ingredients']):
                continue

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


def flat_ingredients_list_BFS(product):
    """
    Recursive function to search the ingredients graph by doing a Breadth First Search and return it as a flat list of
    all nodes.
    Sub ingredients are placed at the end of the list.

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
            nodes += flat_ingredients_list_BFS(ingredient)

            if 'ingredients' in ingredient:
                del ingredient['ingredients']

    return nodes


def flat_ingredients_list_DFS(product):
    """
    Recursive function to search the ingredients graph by doing a Depth First Search and return it as a flat list of
    all nodes.
    Sub ingredients are placed right after their parents.

    Args:
        product (dict): Dict corresponding to a product or a compound ingredient.

    Returns:
        list: List containing all the ingredients graph nodes.
    """
    if 'ingredients' in product:
        product_without_ingredients = copy.deepcopy(product)
        del product_without_ingredients['ingredients']

        if '_id' in product:  # It is a product and not a compound ingredient:
            return [y for x in product['ingredients'] for y in flat_ingredients_list_DFS(x)]
        else:
            return [product_without_ingredients] + [y for x in product['ingredients'] for y in
                                                    flat_ingredients_list_DFS(x)]
    else:
        return [product]


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


def agribalyse_impact_name_i18n(impact_name):
    """
    Returns the French version of an impact name

    Args:
        impact_name (str):

    Examples:
        >>> agribalyse_impact_name_i18n('Climate change')
        'Changement climatique'
        >>> agribalyse_impact_name_i18n("Appauvrissement de la couche d'ozone")
        'Appauvrissement de la couche d'ozone'
    """

    if impact_name in AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR:
        return AGRIBALYSE_IMPACT_CATEGORIES_EN_TO_FR[impact_name]
    elif impact_name in AGRIBALYSE_IMPACT_CATEGORIES_FR:
        return impact_name
    else:
        raise ValueError(f'Unrecognized impact: {impact_name}')
