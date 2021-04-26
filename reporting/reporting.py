import json
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import weasyprint
import matplotlib.pyplot as plt
import pylab
import seaborn as sns

from impacts_estimation.impact_estimation import estimate_impacts_safe
from impacts_estimation.vars import AGRIBALYSE_IMPACT_CATEGORIES, AGRIBALYSE_IMPACT_UNITS
from utils import ensure_extension, get_product_from_barcode
from ingredients_characterization.vars import AGRIBALYSE_DATA_FILEPATH
from data import ingredients_data, off_categories

with open(AGRIBALYSE_DATA_FILEPATH, 'r', encoding='utf8') as file:
    agribalyse_data = {x['ciqual_AGB']: x for x in json.load(file)}


class ProductImpactReport:
    """ Class used to generate reports for Open Food Facts products impacts. """

    def __init__(self, barcode=None, product=None, impact_categories=None, main_impact_category='Score unique EF',
                 product_mass=1000, language='french'):
        """
        Args:
            barcode (str): Barcode of the Open Food Facts product (use only if product is None).
                If this parameter is used, the product will be downloaded from Open Food Facts API.
            product (dict): Open Food Facts product (use only if barcode is None)
            impact_categories (list): Impact categories to consider.
                By default will consider all the impact categories available in Agribalyse.
            main_impact_category (str): Main impact category to display.
            product_mass (float): Mass of product considered in grams
            language (str): Language of the report
        """
        self.impact_categories = impact_categories or AGRIBALYSE_IMPACT_CATEGORIES
        self.main_impact_category = main_impact_category
        self.product_mass = product_mass
        self.language = language.lower()
        self.language_short = language[:2]

        assert self.main_impact_category in AGRIBALYSE_IMPACT_CATEGORIES
        assert all(x in AGRIBALYSE_IMPACT_CATEGORIES for x in self.impact_categories)

        self._html_output = None
        self.images_filepath = {}

        if (barcode is not None) and (product is not None):
            raise ValueError('Both barcode and product parameters cannot be provided simultaneously.')

        if barcode is not None:
            self.product = get_product_from_barcode(barcode)
        elif product is not None:
            self.product = product
        else:
            raise ValueError('Barcode and product parameters cannot be None simultaneously.')

        # Getting reference data from the corresponding Agribalyse product
        try:
            product_agribalyse_data = self.product['ecoscore_data']['agribalyse']
            if 'agribalyse_food_code' in product_agribalyse_data:
                self.agribalyse_proxy_code = product_agribalyse_data['agribalyse_food_code']
            elif 'agribalyse_proxy_food_code' in product_agribalyse_data:
                self.agribalyse_proxy_code = product_agribalyse_data['agribalyse_proxy_food_code']
            else:
                raise KeyError
        except KeyError:
            self.agribalyse_proxy_code = None

        self.has_agribalyse_proxy = self.agribalyse_proxy_code is not None

        if self.agribalyse_proxy_code is not None:
            self.agribalyse_proxy_data = agribalyse_data[self.agribalyse_proxy_code]

            # Getting impact of non agricultural phases
            self.impact_base = {impact_category:
                                    sum([self.agribalyse_proxy_data['impact_environnemental'][impact_category][
                                             'etapes'][
                                             step]
                                         for step in
                                         self.agribalyse_proxy_data['impact_environnemental'][impact_category][
                                             'etapes'].keys()
                                         if step != 'Agriculture']) * product_mass / 1000
                                for impact_category in self.impact_categories}
        else:
            self.agribalyse_proxy_data = None
            self.impact_base = {impact_category: 0
                                for impact_category in self.impact_categories}

        self._compute_impact()

        self.ingredients = list(self.impact_result['ingredients_impacts_share'][self.main_impact_category])
        self.ingredients_without_impact = [x for x in self.ingredients
                                           if (x not in ingredients_data)
                                           or ('impacts' not in ingredients_data[x])]

        self.env = Environment(loader=FileSystemLoader('.'))
        self.template = self.env.get_template("product_impact_report_template.html")

    def _compute_impact(self):
        self.impact_result = estimate_impacts_safe(self.product,
                                                   self.impact_categories,
                                                   quantity=self.product_mass,
                                                   distributions_as_result=True)

    def main_impact_plot(self):
        """ Boxplot of the main impact """

        fig, ax = plt.subplots(figsize=(6, 1.5))

        impact_base = self.impact_base[self.main_impact_category]
        boxes = [
            {
                'label': '',
                'whislo': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.05'],
                'q1': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.25'],
                'med': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.5'],
                'q3': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.75'],
                'whishi': impact_base + self.impact_result['impacts_quantiles'][self.main_impact_category]['0.95'],
            }
        ]
        ax.bxp(boxes,
               vert=False,
               showfliers=False,
               medianprops=dict(linewidth=2),
               boxprops=dict(linewidth=2, color='#555555'),
               whiskerprops=dict(linewidth=2, color='#777777'),
               capprops=dict(linewidth=2, color='#777777'))

        if self.has_agribalyse_proxy:
            ax.axvline(self.agribalyse_proxy_data['impact_environnemental'][self.main_impact_category]['synthese'],
                       linestyle='--',
                       color='darkgreen')

        lower, upper = ax.get_xlim()
        ax.set_xlim(0, upper)
        ax.set_ylim(0.85, 1.15)
        fig.tight_layout()

        return fig

    def impact_per_step_plot(self):
        """
            Stacked bar showing the impacts shares related to each production step.
            Only possible if the product is linked to an Agribalyse reference
        """
        if not self.has_agribalyse_proxy:
            raise Exception("The product has no agribalyse proxy."
                            "No information about productions steps are available.")

        # Creating the figure for the graphic
        fig = pylab.figure()
        ax = fig.add_subplot(111)

        rank = 0.5
        agricultural_impact_value = self.impact_result['impacts_quantiles'][self.main_impact_category]['0.5']
        steps = self.agribalyse_proxy_data['impact_environnemental'][self.main_impact_category]['etapes']
        total = agricultural_impact_value + sum([v for k, v in steps.items() if k != 'Agriculture'])
        for step, value in reversed(steps.items()):
            if step == 'Agriculture':
                value = agricultural_impact_value

            ax.barh(y=rank,
                    width=value / total,
                    height=0.3,
                    left=0,
                    label=step,
                    color='#008040')
            ax.text(x=0.01,
                    y=rank + 0.25,
                    s=f"{step}: {value / total:.1%}")
            rank += 1

        xticks = [0, 0.25, 0.50, 0.75, 1]
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{int(x * 100)}%" for x in xticks])
        ax.set_yticks([])
        ax.set_ylim(0, rank)
        ax.set_xlim(0, 1)
        fig.tight_layout()

        return fig

    def impact_per_ingredient_plot(self):
        """
            Stacked bar showing the impacts shares related to each ingredient step.
        """

        # Creating the figure for the graphic
        fig = pylab.figure()
        ax = fig.add_subplot(111)

        rank = 0.5
        impact_shares = {k: v for k, v
                         in self.impact_result['ingredients_impacts_share'][self.main_impact_category].items()}
        for ingredient, value in sorted(impact_shares.items(), key=lambda x: x[1]):
            ax.barh(y=rank,
                    width=value,
                    height=0.3,
                    left=0,
                    label=ingredient,
                    color='#008040')

            if ingredient in self.ingredients_without_impact:
                text_color = 'darkred'
            else:
                text_color = 'black'

            ax.text(x=0.01,
                    y=rank + 0.25,
                    s=f"{ingredient}: {value:.1%}",
                    color=text_color)
            rank += 1

        xticks = [0, 0.25, 0.50, 0.75, 1]
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{int(x * 100)}%" for x in xticks])
        ax.set_yticks([])
        ax.set_ylim(0, rank)
        ax.set_xlim(0, 1)
        fig.tight_layout()

        return fig

    def ingredient_table_data(self):
        """ Return a list of dict containing data on the ingredients """

        impact_shares = sorted(self.impact_result['ingredients_impacts_share'][self.main_impact_category].items(),
                               key=lambda x: x[1] or 0, reverse=True)

        result = []
        agricultural_impact_value = self.impact_result['impacts_quantiles'][self.main_impact_category]['0.5']
        impact_base = self.impact_base[self.main_impact_category]
        total_impact = agricultural_impact_value + impact_base
        for ingredient_id, ingredient_share in impact_shares:
            row_data = {'id': ingredient_id}

            if ingredient_share is not None:
                # Inflating the ingredient share to take base impact into account
                row_data['impact_share'] = ingredient_share * total_impact
                row_data['impact_share_prct'] = 100 * ingredient_share
            else:
                row_data['impact_share'] = None
                row_data['impact_share_prct'] = None

            result.append(row_data)

            try:
                row_data['nutritional_references'] = \
                    [x['entry'] for x in ingredients_data[ingredient_id]['nutritional_data_sources']]
            except KeyError:
                row_data['nutritional_references'] = []

            try:
                row_data['environmental_references'] = \
                    [x['entry'] for x in ingredients_data[ingredient_id]['environmental_impact_data_sources']]
            except KeyError:
                row_data['environmental_references'] = []

        return result

    def impacts_data(self):

        result = dict()
        for impact_category in self.impact_categories:
            impact_data = {
                'category': impact_category,
                'unit': AGRIBALYSE_IMPACT_UNITS[impact_category],
                'confidence_interval': ''
            }

            if impact_category in self.impact_result['impacts_quantiles']:
                impact_data['amount'] = self.impact_result['impacts_quantiles'][impact_category]['0.5']
            else:
                impact_data['amount'] = "This impact could not be calculated."

            if impact_category in self.impact_result['impacts_quantiles']:
                impact_data['conf_int_lower_bound'] = self.impact_result['impacts_quantiles'][impact_category]['0.05']
            else:
                impact_data['conf_int_lower_bound'] = "This impact could not be calculated."

            if impact_category in self.impact_result['impacts_quantiles']:
                impact_data['conf_int_upper_bound'] = self.impact_result['impacts_quantiles'][impact_category]['0.95']
            else:
                impact_data['conf_int_upper_bound'] = "This impact could not be calculated."

            if self.has_agribalyse_proxy:
                impact_data['reference_impact'] = \
                    self.agribalyse_proxy_data['impact_environnemental'][impact_category]['synthese']

            result[impact_category] = impact_data

        return result

    def off_categories(self):
        """ Getting the names of the OFF categories in the desired language. """
        result = []
        for category in self.product['categories_tags']:
            try:
                category_name = off_categories[category]['name'].get(self.language_short,
                                                                     off_categories[category]['name']['en'])
                result.append(category_name)
            except KeyError:
                result.append(category)

        return result

    def _generate_figure(self, plotting_function, figure_name, img_folder=None):
        fig = plotting_function()
        if img_folder is not None:
            filepath = Path.cwd() / img_folder / f"{str(uuid.uuid4())[:8]}.png"
            filepath.parent.mkdir(parents=True, exist_ok=True)
        else:
            filepath = Path.cwd() / f"{str(uuid.uuid4())[:8]}.png"
        self.images_filepath[figure_name] = filepath
        fig.savefig(filepath, bbox_inches='tight')

    def _generate_figures(self, img_folder=None):
        """ Generating the figures png files """

        sns.set()

        # Main impact plot
        self._generate_figure(plotting_function=self.main_impact_plot,
                              figure_name='main_impact_plot',
                              img_folder=img_folder)

        # Impact per step plot
        if self.has_agribalyse_proxy:
            self._generate_figure(plotting_function=self.impact_per_step_plot,
                                  figure_name='impact_per_step_plot',
                                  img_folder=img_folder)

        # Impact per ingredient
        self._generate_figure(plotting_function=self.impact_per_ingredient_plot,
                              figure_name='impact_per_ingredient_plot',
                              img_folder=img_folder)

    def _clear_images(self):
        """ Deletes the images generated """
        for image_filepath in self.images_filepath.values():
            image_filepath.unlink()

    def _generate_html(self):
        """ Generate the html version of the report """

        template_vars = {"product_name": self.product.get('product_name'),
                         "barcode": self.product['_id'],
                         "main_impact_category": self.main_impact_category,
                         "has_agribalyse_proxy": self.has_agribalyse_proxy,
                         "reference_agb_product":
                             self.agribalyse_proxy_data['nom_francais'] if self.has_agribalyse_proxy else None,
                         "has_ingredients_without_impact": len(self.ingredients_without_impact) > 0,
                         "product_mass": self.product_mass,
                         "ingredients_data": self.ingredient_table_data(),
                         "images_filepath": self.images_filepath,
                         "off_categories": self.off_categories(),
                         "total_mass_used": self.impact_result['average_total_used_mass'],
                         "full_ingredient_list": self.product['ingredients_text'],
                         "impacts_data": self.impacts_data(),
                         "result_warnings": self.impact_result['warnings'],
                         "reliability": str(self.impact_result['reliability'])
                         }

        self._html_output = self.template.render(template_vars)

    def to_pdf(self, filename=None):
        """ Export the result to pdf """

        filename = filename or self.product.get('product_name') or self.product['_id']
        filename = ensure_extension(filename, 'pdf')

        try:
            self._generate_figures()
            self._generate_html()
            weasyprint.HTML(string=self._html_output, base_url='.').write_pdf(filename)
        finally:
            self._clear_images()

    def to_html(self, filename=None):
        filename = filename or self.product.get('product_name') or self.product['_id']
        filename = ensure_extension(filename, 'html')

        self._generate_figures(img_folder=Path(filename).stem)
        self._generate_html()
        with open(filename, 'w') as file:
            file.write(self._html_output)
