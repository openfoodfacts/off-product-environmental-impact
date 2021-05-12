import copy

import pytest

from impacts_estimation.impacts_estimation import ImpactEstimator
from impacts_estimation.exceptions import NoCharacterizedIngredientsError, NoKnownIngredientsError
from impacts_estimation.utils import flat_ingredients_list_DFS
from data import ingredients_data, off_taxonomy
from tests.test_data import pound_cake


class TestImpactEstimator:
    def setup_method(self):
        self.product = copy.deepcopy(pound_cake)

    def test_raise_no_characterized_ingredients_error(self):
        """ Ensures a NoCharacterizedIngredientsError is raised if no ingredient of the product are characterized. """

        uncharacterized_ingredient_1, uncharacterized_ingredient_2 = [ing for ing in off_taxonomy if
                                                                      ing not in ingredients_data][:2]

        product = {'_id': '',
                   'ingredients': [{'id': uncharacterized_ingredient_1},
                                   {'id': uncharacterized_ingredient_2}],
                   'nutriments': {'carbohydrates_100g': 30,
                                  'fat_100g': 20}}

        with pytest.raises(NoCharacterizedIngredientsError):
            ImpactEstimator(product)

    def test_raise_no_known_ingredients_error(self):
        """ Ensures a NoKnownIngredientsError is raised if no ingredient of the product are known. """

        product = {'_id': '',
                   'ingredients': [{'id': 'unknown_ingredient_1'},
                                   {'id': 'unknown_ingredient_2'}],
                   'nutriments': {'carbohydrates_100g': 30,
                                  'fat_100g': 20}}

        with pytest.raises(NoKnownIngredientsError):
            ImpactEstimator(product)

    def test_defined_percentage_ok(self):
        """ Ensures that if the defined percentages of ingredients are ok, they are used. """

        self.product['ingredients'][1]['percent'] = 25
        self.product['ingredients'][2]['percent'] = 20

        impact_estimator = ImpactEstimator(product=self.product, use_defined_prct=True)

        assert impact_estimator.use_defined_prct is True

    def test_wrong_defined_percentage_order(self):
        """ Ensures that if the defined percentages of ingredients are not in decreasing order, they are not used. """

        self.product['ingredients'][1]['percent'] = 20
        self.product['ingredients'][2]['percent'] = 25

        impact_estimator = ImpactEstimator(product=self.product, use_defined_prct=True)

        assert impact_estimator.use_defined_prct is False

    def test_percentage_outside_natural_bounds(self):
        """
            Ensures that if the defined percentage of an ingredient is not within its natural bounds, it is not used.
        """

        self.product['ingredients'][1]['percent'] = 55

        impact_estimator = ImpactEstimator(product=self.product, use_defined_prct=True)

        assert 'percent' not in impact_estimator.product['ingredients'][1]

    def test_percentage_prevent_sum_under_105(self):
        """
            Ensures that if the defined percentages of ingredients prevents the total to be under 105, they are not
             used.
        """

        self.product['ingredients'][0]['percent'] = 80
        self.product['ingredients'][1]['percent'] = 40

        impact_estimator = ImpactEstimator(product=self.product, use_defined_prct=True)

        assert impact_estimator.use_defined_prct is False

    def test_percentage_prevent_sum_over_95(self):
        """
            Ensures that if the defined percentages of ingredients prevents the total to be over 95, they are not
             used.
        """

        self.product['ingredients'][0]['percent'] = 25
        self.product['ingredients'][1]['percent'] = 2

        impact_estimator = ImpactEstimator(product=self.product, use_defined_prct=True)

        assert impact_estimator.use_defined_prct is False

    def test_get_impact_result(self):
        """ Assert that an impact result is returned if the product is ok. """

        impact_estimator = ImpactEstimator(product=self.product)
        impact_result = impact_estimator.estimate_impacts('Score unique EF')

        assert isinstance(impact_result['impacts_geom_means']['Score unique EF'], float)

    def test_get_several_impact_result(self):
        """ Assert that an impact result is returned for several impacts. """

        impact_estimator = ImpactEstimator(product=self.product)
        impact_result = impact_estimator.estimate_impacts(['Score unique EF', 'Particules'])

        assert isinstance(impact_result['impacts_geom_means']['Score unique EF'], float)
        assert isinstance(impact_result['impacts_geom_means']['Particules'], float)

    def test_get_impact_result_in_english(self):
        """
            Assert that an impact result is returned for an impact name in English and that the result keeps the impact
             name in English.
        """

        impact_estimator = ImpactEstimator(product=self.product)
        impact_result = impact_estimator.estimate_impacts('Climate change')

        assert isinstance(impact_result['impacts_geom_means']['Climate change'], float)

    def test_ingredients_impact_share(self):
        """ Assert that the ingredients impact shares are returned """

        impact_estimator = ImpactEstimator(product=self.product)
        impact_result = impact_estimator.estimate_impacts('Climate change')

        for ingredient in flat_ingredients_list_DFS(self.product):
            assert isinstance(impact_result['ingredients_impacts_share']['Climate change'][ingredient['id']], float)

    def test_impacts_units(self):
        """ Assert that the impacts units are returned """

        impact_estimator = ImpactEstimator(product=self.product)
        impact_result = impact_estimator.estimate_impacts('Climate change')

        assert isinstance(impact_result['impacts_units']['Climate change'], str)

    def test_remove_allergens(self):
        """
            Assert that if an allergen is present in the ingredient list it will be removed and not considered as a
            subingredient.
        """

        self.product['allergens_tags'] = ["en:soybeans"]
        self.product['ingredients'].append({'id': 'ingredient containing allergen',
                                            'ingredients': [{'id': 'en:soya-lecithin'}]})
        impact_estimator = ImpactEstimator(product=self.product)

        assert 'en:soya-lecithin' not in [x['id'] for x in flat_ingredients_list_DFS(impact_estimator.product)]
