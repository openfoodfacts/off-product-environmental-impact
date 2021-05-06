import copy

import pytest

from impacts_estimation.impacts_estimation import RandomRecipeCreator, RecipeCreationError
from tests.test_data import pound_cake


class TestRandomRecipeCreator:
    def setup_method(self):
        self.product = copy.deepcopy(pound_cake)

    def test_crash_if_impossible_recipe(self):
        """ Assert that a RecipeCreationError is raised if there is no possible recipe. """

        product = self.product
        product['nutriments']['carbohydrates_100g'] = 0.1

        random_recipe_creator = RandomRecipeCreator(product)

        with pytest.raises(RecipeCreationError):
            random_recipe_creator.random_recipe()

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

        assert round(sum(recipe.values()), 3) == 110
