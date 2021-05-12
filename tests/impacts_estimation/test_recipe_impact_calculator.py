from impacts_estimation.impacts_estimation import RecipeImpactCalculator

recipe = {'en:egg': 40,
          'en:milk': 35,
          'en:sugar': 25}


def test_recipe_impact_calculator_gives_result():
    impact_calculator = RecipeImpactCalculator(recipe, impact_name='Score unique EF')

    assert isinstance(impact_calculator.get_recipe_impact(), float)
    assert isinstance(impact_calculator.get_ingredient_impact_share('en:egg'), float)


def test_recipe_impact_calculator_with_english_impact():
    impact_calculator = RecipeImpactCalculator(recipe, impact_name='Climate change')

    assert isinstance(impact_calculator.get_recipe_impact(), float)
    assert isinstance(impact_calculator.get_ingredient_impact_share('en:egg'), float)
