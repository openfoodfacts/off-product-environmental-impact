Food product modelling
======================

Among other information, the Open Food Facts database contains the ingredient list and nutritional composition of each product. Coupling this information to physical and regulatory constraints makes it possible to guess the recipe of the product. In order to do this, the following conceptual framework have been developed.

Let a product of mass :math:`F` be composed of a set of ingredients :math:`I`. Let :math:`M` be the total mass of ingredients used
before processing. The ingredients processing may induce a water loss (cooking or drying for example), thus:

.. math::
    M \ge F

Let :math:`m_i` be the mass of ingredient :math:`i \in I` used and :math:`p_i` its proportion of the total mass :math:`M`.

.. math::
    M = \sum_{i \in I}{m_i}\\
    \forall i \in I, m_i = M \cdot p_i\\

:math:`F` is known but :math:`M` is not and the proportions :math:`p_i` are generally not. However, the impacts of the product depend on the masses of ingredients :math:`m_i`.

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_total_leaves_percentage_constraint`

Ingredients order
-----------------

The ingredient list is given by decreasing proportion at the moment of incorporation in the product, if this proportion is superior to 2%.

.. math::
    \forall i \in I, p_{i+1} \le \max(p_i, 0.02)

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_mass_order_constraints` and :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._remove_decreasing_order_constraint_from_rank`.

Compound ingredients
--------------------

The ingredients composing a food product can themselves be composed by sub-ingredients. Let :math:`i` be an ingredient of :math:`I`. Let :math:`J` be the set of ingredients composing :math:`i`. Let :math:`m_j` be the mass of ingredient :math:`j \in J` used and :math:`p_j` its proportion of the mass :math:`m_i`.

.. math::
    m_i = \sum_{j \in J}{m_j}\\
    \forall j \in J, m_j = m_i \cdot p_j\\

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_total_subingredients_percentages_constraint`

Nutriments balance
------------------

Let :math:`N` be the set of nutrient types considered. Let :math:`F_n` be the mass of the nutrient :math:`n \in N` in the product according to its packaging information. This mass has an error margin depending on its value which can be relative (in percent) or absolute (in grams). Let :math:`M_n` be the mass of nutriment :math:`n \in N` actually contained in the product.


.. table:: Nutriment information error margins (source: INCO EU regulation)
    :align: center

    +-------------------------------+------------------+--------------+
    | Nutrient                      | Content (g/100g) | Error margin |
    +===============================+==================+==============+
    | Carbohydrates, sugars,        | <10              | ±2g          |
    | proteins, fibers              +------------------+--------------+
    |                               | [10 – 40]        | ±20%         |
    |                               +------------------+--------------+
    |                               | >40              | ±8g          |
    +-------------------------------+------------------+--------------+
    | Fats                          | <10              | ±1.5g        |
    |                               +------------------+--------------+
    |                               | [10 – 40]        | ±20%         |
    |                               +------------------+--------------+
    |                               | >40              | ±8g          |
    +-------------------------------+------------------+--------------+
    | Saturated fats                | <10              | ±1.5g        |
    |                               +------------------+--------------+
    |                               | [10 – 40]        | ±20%         |
    |                               +------------------+--------------+
    |                               | >40              | ±8g          |
    +-------------------------------+------------------+--------------+
    | Sodium                        | <0.5             | ±0.15g       |
    |                               +------------------+--------------+
    |                               | >0.5             | ±20%         |
    +-------------------------------+------------------+--------------+
    | Salt                          | <1.25            | ±0.375g      |
    |                               +------------------+--------------+
    |                               | >1.25            | ±20%         |
    +-------------------------------+------------------+--------------+

This error margin can be modeled as two separate margins :math:`\varepsilon_n` and :math:`\delta_n`, respectively absolute and relative, with one and only one of them being non-zero. We note :math:`c_{n,i}` (resp. :math:`m_{n,i}`) the content (resp. mass) of nutrient :math:`n` in the ingredient :math:`i`.


.. math::
    \forall n \in N, (1 - \delta_n) F_n - \varepsilon_n &\le M_n \le (1 + \delta_n) F_n + \varepsilon_n   \\
    (1 - \delta_n) F_n - \varepsilon_n &\le \sum_{i \in I}{m_{n,i}}  \le (1 + \delta_n) F_n + \varepsilon_n   \\
    (1 - \delta_n) F_n - \varepsilon_n &\le M \sum_{i \in I}{p_i \cdot c_{n,i}}  \le (1 + \delta_n) F_n + \varepsilon_n

The nutrient content of ingredients is not necessarily known but it can be bounded by the values :math:`c_{min,n,i}` and :math:`c_{max,n,i}`.

.. math::
    \forall n \in N, \forall i \in I, 0 \le c_{min,n,i} \le c_{n,i} \le c_{max,n,i} \le 1

Thus:

.. math::
    M\sum_{i \in I}{p_i\cdot c_{max,n,i}} \ge (1 - \delta) F_n - \varepsilon_n  \\
    M\sum_{i \in I}{p_i\cdot c_{min,n,i}} \le (1 + \delta) F_n + \varepsilon_n

.. note::
    These equations are implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_nutritional_constraints`.
    :func:`~impacts_estimation.utils.nutritional_error_margin` gives the relative and absolute margin for a nutriment and a value.

Water balance
-------------

Evaporation is modeled as a proportion :math:`E` of the water in each ingredient that is lost during the product processing. Let :math:`c_{w,i}` be the water content of ingredient :math:`i`.

.. math::
    F &= M - E \sum_{i \in I}{m_i \cdot c_{w,i}} \\
    F &= M \left( 1- E \sum_{i \in I}{p_i \cdot c_{w,i}} \right)

Considering that the water content :math:`c_{w,i}` of ingredient :math:`i` is between two bounds :math:`c_{min,w,i}` and :math:`c_{max,w,i}`, we have:

.. math::
    \forall i \in I, 0 \le c_{min,w,i} \le c_{w,i} \le c_{max,w,i} \le 1

Thus:

.. math::
        M \left(1 - E \sum_{i \in I} p_i \cdot c_{max,w,i}\right) \le F \le M \left(1 - E \sum_{i \in I} p_i \cdot c_{min,w,i}\right)

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_evaporation_constraint`

Moreover, :math:`F` can be used to bound the value of the total mass used :math:`M`.
Indeed, in the case where the product is only made of water, we have:

.. math::
    F = M(1-E)

By extending it to the general case, we can deduce:

.. math::
    F \le M \le \frac{F}{1-E}

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_used_mass_constraint`

Mass balance
------------

Considering that food products consist only of water and nutrients, we have:

.. math::
    F &= \sum_{i \in I}{m_i \cdot c_{w,i} \cdot (1-E) } + \sum_{n \in N}{F_n} \nonumber \\
    F &= \sum_{i \in I}{m_i \cdot c_{w,i} \cdot (1-E) } + \sum_{i \in I}{\sum_{n \in N}{m_i \cdot c_{n,i}}} \nonumber \\
    F &= \sum_{i \in I}{m_i \left( (1-E) c_{w,i} + \sum_{n \in N}{c_{n,i}}\right)} \nonumber \\
    F &= M\sum_{i \in I}{p_i \left( (1-E) c_{w,i} + \sum_{n \in N}{c_{n,i}}\right)} \nonumber \\

.. math::
    M\sum_{i \in I}{p_i \left( (1-E) c_{min,w,i} + \sum_{n \in N}{c_{min,n,i}}\right)} \le F \le M\sum_{i \in I}{p_i \left( (1-E) c_{max,w,i} + \sum_{n \in N}{c_{max,n,i}}\right)}

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RandomRecipeCreator._add_product_mass_constraint`

Product environmental impact
----------------------------

Let :math:`C` be a set of environmental impact categories, we note :math:`\alpha_{c,i}` the mass impact of ingredient :math:`i` in category :math:`c`.
Let us consider a product composed of a set of ingredients :math:`I`.
The impact :math:`A_c` of the product in category :math:`c` is defined by the sum of the used mass of its ingredients weighted by their impact per mass unit.

.. math::
    \forall c \in C, A_c = \sum_{i\in I} m_i \cdot \alpha_{c,i}

.. note::
    This equation is implemented by :meth:`~impacts_estimation.impacts_estimation.RecipeImpactCalculator._compute_impact`