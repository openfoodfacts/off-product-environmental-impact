from impacts_estimation.impacts_estimation import RecipeImpactCalculator


def test_recipe_impact_calculator():
    recipe = {'en:egg': 40,
              'en:milk': 35,
              'en:sugar': 25}

    impact_calculator = RecipeImpactCalculator(recipe, impact_name='Score unique EF')

    assert type(impact_calculator.get_recipe_impact()) == float
    assert type(impact_calculator.get_ingredient_impact_share('en:egg')) == float
