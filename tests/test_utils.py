""" Testing functions and classes in impacts_estimation.utils """

from impacts_estimation.utils import nutriments_from_recipe, confidence_score


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


