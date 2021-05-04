""" Testing functions and classes in impacts_estimation.utils """

from impacts_estimation.utils import nutriments_from_recipe, confidence_score, clear_ingredient_graph, \
    minimum_percentage_sum, maximum_percentage_sum, define_subingredients_percentage_type, flat_ingredients_list_BFS, \
    flat_ingredients_list_DFS, find_ingredients_graph_leaves, UnknownIngredientsRemover, remove_percentage_from_product, \
    weighted_geometric_mean


def test_nutri_from_recipe():
    recipe = {'en:flour': 55, 'en:egg': 25, 'en:milk': 20}

    nutriments = nutriments_from_recipe(recipe)

    assert 'proteins' in nutriments
    assert 'carbohydrates' in nutriments
    assert 'fat' in nutriments
    assert 'fiber' in nutriments
    assert 'salt' in nutriments
    assert 'sugars' in nutriments
    assert 'saturated-fat' in nutriments


def test_confidence_score_nutri_component():
    """
        Test that the confidence score of a nutritional composition is higher if the composition is close to the
        reference
    """

    reference_nutri = {'proteins': 10,
                       'carbohydrates': 50,
                       'fat': 20,
                       'fiber': 10,
                       'salt': 1,
                       'sugars': 10,
                       'saturated-fat': 10}

    nutri_close = {'proteins': 12,
                   'carbohydrates': 51,
                   'fat': 19,
                   'fiber': 10,
                   'salt': 1,
                   'sugars': 11,
                   'saturated-fat': 9}

    nutri_far = {'proteins': 30,
                 'carbohydrates': 30,
                 'fat': 20,
                 'fiber': 10,
                 'salt': 1,
                 'sugars': 5,
                 'saturated-fat': 5}

    conf_score_close = confidence_score(nutri_close,
                                        reference_nutri,
                                        total_mass=100,
                                        min_possible_mass=100,
                                        max_possible_mass=150)

    conf_score_far = confidence_score(nutri_far,
                                      reference_nutri,
                                      total_mass=100,
                                      min_possible_mass=100,
                                      max_possible_mass=150)

    assert conf_score_close > conf_score_far


def test_confidence_score_total_mass_component():
    """
        Assert than with the same nutritional composition, a recipe has a better confidence score if its total mass is
        near 100g.
    """

    reference_nutri = {'proteins': 10,
                       'carbohydrates': 50,
                       'fat': 20,
                       'fiber': 10,
                       'salt': 1,
                       'sugars': 10,
                       'saturated-fat': 10}

    conf_score_lower_mass = confidence_score(reference_nutri,
                                             reference_nutri,
                                             total_mass=75,
                                             min_possible_mass=50,
                                             max_possible_mass=150)

    conf_score_exact_mass = confidence_score(reference_nutri,
                                             reference_nutri,
                                             total_mass=100,
                                             min_possible_mass=50,
                                             max_possible_mass=150)

    conf_score_higher_mass = confidence_score(reference_nutri,
                                              reference_nutri,
                                              total_mass=125,
                                              min_possible_mass=50,
                                              max_possible_mass=150)

    assert conf_score_higher_mass < conf_score_exact_mass
    assert conf_score_lower_mass < conf_score_exact_mass


def test_clear_ingredient_graph():
    """ Assert that subingredients are removed only if none of them has a percentage or is characterized """

    product = {'_id': '000',
               'ingredients': [
                   {
                       'id': 'en:flour',
                       'ingredients': [
                           {'id': 'uncharacterized_subingredient_1'},
                           {'id': 'uncharacterized_subingredient_2'}
                       ]
                   },
                   {
                       'id': 'en:milk',
                       'ingredients': [
                           {'id': 'uncharacterized_subingredient_1'},
                           {
                               'id': 'uncharacterized_subingredient_with_percentage',
                               'percent': 4
                           }
                       ]
                   },
                   {
                       'id': 'en:sugar',
                       'ingredients': [
                           {'id': 'uncharacterized_subingredient_1'},
                           {'id': 'en:water'}
                       ]
                   }
               ]
               }

    clear_ingredient_graph(product)

    assert 'ingredients' not in product['ingredients'][0]
    assert 'ingredients' in product['ingredients'][1]
    assert 'ingredients' in product['ingredients'][2]


def test_minimum_percentage_sum():
    ingredients = [{'id': 'ingredient_1'},
                   {'id': 'ingredient_2',
                    'percent': 20},
                   {'id': 'ingredient_3',
                    'percent': 10}
                   ]

    assert minimum_percentage_sum(ingredients) == 50


def test_maximum_percentage_sum():
    ingredients = [{'id': 'ingredient_1',
                    'percent': 30},
                   {'id': 'ingredient_2'},
                   {'id': 'ingredient_3',
                    'percent': 10}
                   ]

    assert maximum_percentage_sum(ingredients) == 70


def test_define_subingredients_percentage_type():
    product_in_percent_of_parent = {'_id': '',
                                    'ingredients': [{'id': 'ingredient_1',
                                                     'percent': 10,
                                                     'ingredients': [{'id': 'ingredient_1'},
                                                                     {'id': 'ingredient_2',
                                                                      'percent': 20},
                                                                     {'id': 'ingredient_3',
                                                                      'percent': 10}
                                                                     ]}
                                                    ]
                                    }

    product_in_absolute_percent = {'_id': '',
                                   'ingredients': [{'id': 'ingredient_1',
                                                    'percent': 10,
                                                    'ingredients': [{'id': 'ingredient_1',
                                                                     'percent': 6},
                                                                    {'id': 'ingredient_2'},
                                                                    {'id': 'ingredient_3',
                                                                     'percent': 2}
                                                                    ]}
                                                   ]
                                   }

    product_in_undefined_percent = {'_id': '', 'ingredients': [{'id': 'ingredient_1',
                                                                'ingredients': [{'id': 'ingredient_1'},
                                                                                {'id': 'ingredient_2',
                                                                                 'percent': 20},
                                                                                {'id': 'ingredient_3',
                                                                                 'percent': 10}
                                                                                ]}
                                                               ]
                                    }

    define_subingredients_percentage_type(product_in_percent_of_parent)
    define_subingredients_percentage_type(product_in_absolute_percent)
    define_subingredients_percentage_type(product_in_undefined_percent)

    assert product_in_percent_of_parent['ingredients'][0]['percent-type'] == 'parent'
    assert product_in_absolute_percent['ingredients'][0]['percent-type'] == 'product'
    assert product_in_undefined_percent['ingredients'][0]['percent-type'] == 'undefined'


def test_flat_ingredients_list_BFS():
    product = {'_id': '',
               'ingredients': [
                   {'id': 'A'},
                   {'id': 'B',
                    'ingredients': [{'id': 'B-A'},
                                    {'id': 'B-B'}]},
                   {'id': 'C'}
               ]}

    assert flat_ingredients_list_BFS(product) == [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}, {'id': 'B-A'}, {'id': 'B-B'}]


def test_flat_ingredients_list_DFS():
    product = {'_id': '',
               'ingredients': [
                   {'id': 'A'},
                   {'id': 'B',
                    'ingredients': [{'id': 'B-A'},
                                    {'id': 'B-B'}]},
                   {'id': 'C'}
               ]}

    assert flat_ingredients_list_DFS(product) == [{'id': 'A'}, {'id': 'B'}, {'id': 'B-A'}, {'id': 'B-B'}, {'id': 'C'}]


def test_find_ingredients_graph_leaves():
    product = {'_id': '',
               'ingredients': [
                   {'id': 'A'},
                   {'id': 'B',
                    'ingredients': [{'id': 'B-A'},
                                    {'id': 'B-B'}]},
                   {'id': 'C'}
               ]}

    assert find_ingredients_graph_leaves(product) == [{'id': 'A'}, {'id': 'B-A'}, {'id': 'B-B'}, {'id': 'C'}]


def test_unknown_ingredients_remover():
    unknown_ingredients_remover = UnknownIngredientsRemover()

    product = {'_id': '',
               'ingredients': [
                   {'id': 'en:egg'},
                   {'id': 'unknown_ingredient_1'},
                   {'id': 'unknown_ingredient_2',
                    'percent': 10},
                   {'id': 'unknown_ingredient_3',
                    'ingredients': [
                        {'id': 'en:flour'}
                    ]},
                   {'id': 'en:milk'}
               ]}

    unknown_ingredients_remover.remove_unknown_ingredients(product)

    assert [x['id'] for x in product['ingredients']] == ['en:egg', 'unknown_ingredient_2', 'unknown_ingredient_3',
                                                         'en:milk']
    assert unknown_ingredients_remover.removed_unknown_ingredients == ['unknown_ingredient_1']


def test_remove_percentage_from_product():
    product_with_prct = {'_id': '',
                         'ingredients': [
                             {'id': 'A',
                              'percent': 10},
                             {'id': 'B',
                              'ingredients': [
                                  {'id': 'BA'},
                                  {'id': 'BB',
                                   'percent': 20}
                              ]},
                         ]}

    product_without_prct = {'_id': '',
                            'ingredients': [
                                {'id': 'A'},
                                {'id': 'B',
                                 'ingredients': [
                                     {'id': 'BA'},
                                     {'id': 'BB'}
                                 ]},
                            ]}

    remove_percentage_from_product(product_with_prct)

    assert product_with_prct == product_without_prct


def test_weighted_geometric_mean():
    values = [4, 36, 9, 6.4, 55]
    weights = [1, 5, 8, 2, 1.2]

    assert round(weighted_geometric_mean(values, weights), 4) == 14.0092
