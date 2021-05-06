import pytest

from impacts_estimation.impacts_estimation import RandomRecipeCreator, RecipeCreationError


def test_crash_if_impossible_recipe():
    """
        Assert that a RecipeCreationError is raised if there is no possible recipe (product with very fat ingredients
        and low fat in the nutritional composition).
    """

    product = {'_id': '',
               'ingredients': [{'id': 'en:palm-oil'},
                               {'id': 'en:butter'}],
               'nutriments': {'carbohydrates_100g': 30,
                              'fat_100g': 3,
                              'proteins_100g': 25,
                              'sugars_100g': 20}}

    random_recipe_creator = RandomRecipeCreator(product)

    with pytest.raises(RecipeCreationError):
        random_recipe_creator.random_recipe()


class TestPossibleRecipe:
    """ Test with a possible recipe of pound cake """

    def setup_method(self):
        self.product = {'_id': '',
                        'ingredients': [{'id': 'en:egg'},
                                        {'id': 'en:flour'},
                                        {'id': 'en:butter'},
                                        {'id': 'en:sugar'}],
                        'nutriments': {'carbohydrates_100g': 46,
                                       'fat_100g': 26,
                                       'saturated-fat_100g': 15.8,
                                       'proteins_100g': 6,
                                       'sugars_100g': 27}}

    def test_get_result_if_possible_recipe(self):
        """ Assert that a result is returned if a recipe is possible."""

        random_recipe_creator = RandomRecipeCreator(self.product)
        recipe = random_recipe_creator.random_recipe()

        assert recipe['en:egg'] > 10
        assert recipe['en:flour'] > 10
        assert recipe['en:butter'] > 10
        assert recipe['en:sugar'] > 10

    def test_total_mass_used_specified(self):
        """ Assert that the returned recipe respects the total mass used parameter. """

        random_recipe_creator = RandomRecipeCreator(self.product, total_mass_used=110)
        recipe = random_recipe_creator.random_recipe()

        assert sum(recipe.values()) == 110
