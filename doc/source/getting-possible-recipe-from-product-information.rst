Getting possible recipe from product information
================================================

The class :class:`~impacts_estimation.impact_estimation.RandomRecipeCreator` can be used to guess a product recipe from its ingredient list and nutritional composition.

.. warning::
    The resulting recipe is **not the most likely** but is simply one possible recipe among many. Due to its random nature, multiple uses of this class with the same product input will result in different recipes output.

Algorithm overview
------------------

The algorithm is based on the use of a nonlinear optimization solver and a technique called *Optimization-Based Bound Tightening* to deduce the ranges of possible values of the percentages of each ingredient respecting the constraints of the system by successively maximizing and minimizing it.
Once this range has been delimited, it is then possible to draw a random percentage value for each ingredient.

In order to illustrate the operation of this algorithm, let us take a simplified system composed of three ingredients :math:`a`, :math:`b` and :math:`b` and whose only constraints are :math:`m_a+m_b+m_c=100` and :math:`m_a > m_b > m_c` . Since the total mass of the ingredients is equal to 100, we can represent this system in a ternary diagram.

.. image:: /_static/ternary_diagram_1.svg
    :width: 300
    :align: center

Considering the decreasing proportions constraint, we can reduce the set of possible solutions:

.. image:: /_static/ternary_diagram_2.svg
    :width: 300
    :align: center

We then randomly choose an ingredient and determine the bounds of the possible values of its mass. For example, the mass of ingredient :math:`b` is in the interval :math:`[0; 50]`. We then randomly choose the value :math:`20`. The set of possible solutions becomes even smaller.

.. image:: /_static/ternary_diagram_3.svg
    :width: 300
    :align: center

By randomly choosing a second ingredient, :math:`a` for example, we can determine the bounds of its mass with the new constraint :math:`m_b = 20`. This implies :math:`m_a ∈ [60; 80]`. We choose a random value in this interval, :math:`78` for
for example. This leaves only one solution which is :math:`{m_a ; m_b ; m_c } = \{78; 20; 2\}`.

.. image:: /_static/ternary_diagram_4.svg
    :width: 300
    :align: center

Setting up the solver
---------------------

The solver used for the *Optimization-Based Bound Tightening* is `SCIP <https://www.scipopt.org/>`_, with its Python interface `PySCIPOpt <https://github.com/scipopt/PySCIPOpt>`_.

Solver parameters
+++++++++++++++++

The constructor of :class:`~impacts_estimation.impact_estimation.RandomRecipeCreator` accepts parameters related to the solver setting.

* :code:`dual_gap_type` allows to choose the type of measurement of the `duality gap <https://en.wikipedia.org/wiki/Duality_gap>`_. It can be seen as an expression of whether the precision of the variable optimization must be absolute or relative.
* :code:`dual_gap_limit` determines the precision of the variable optimization by the solver. Relative or absolute according to dual_gap_type.
* :code:`solver_time_limit` allows to set a maximum time for the solver optimization (in seconds). Set to None or 0 to set no limit.
* :code:`time_limit_dual_gap_limit` allows to set an alternative precision in case of time limit hit. If the time limit is hit and the duality gap is still higher than this parameter, a :class:`~impacts_estimation.exceptions.RecipeCreationError` is raised.

Solver variables
++++++++++++++++

Using the conceptual framework detailed in :ref:`Food product modelling`, :class:`~impacts_estimation.impact_estimation.RandomRecipeCreator` implements solver variables for the following:

* The attribute :code:`total_mass_var` corresponds to the total mass of ingredients used before transformation :math:`M`
* The attribute :code:`evaporation_var` corresponds to the evaporation coefficient :math:`E`
* The variables stored in the :code:`ingredient_vars` dictionary correspond to the proportions of ingredients :math:`p_i, i \in I`

The other components of the model such as the minimum and maximum nutrients and water content of ingredients are considered as constants and are given in :code:`ingredients_data.json` (see :ref:`Ingredients characterization`).

Solver constraints
++++++++++++++++++

The constraints of the variables corresponding to the equations detailed in :ref:`Food product modelling` are added to the solver by dedicated methods:

* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_total_leaves_percentage_constraint`
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_mass_order_constraints`
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._remove_decreasing_order_constraint_from_rank`
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_total_subingredients_percentages_constraint`,
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_nutritional_constraints`
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_evaporation_constraint`
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_used_mass_constraint`
* :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._add_product_mass_constraint`

In some cases, imperfections of the food product modelling or erroneous data can lead to an empty space of possible solutions. The parameter :code:`const_relax_coef` can help to overcome this limitation by relaxing the constraints and then expending the space of possible solutions.

Choosing the ingredient proportion
----------------------------------

The main element of this algorithm is a loop on all ingredients in random order to identify their proportion's bounds and then randomly choose a value within these bounds.

Getting the bounds of an proportion of the ingredient is done with the method :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._get_variable_bounds` that will simply call :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._optimize_variable` to successively maximize and minimize the variable corresponding to the ingredient's proportion.

Once the bounds of the ingredient's proportion are defined, :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator._pick_proportion` will randomly choose a proportion within these bounds by one of the following ways:

* If there is less than :code:`min_prct_dist_size` products in Open Food Facts that has a percentage value within the given bounds for this ingredient, the proportion is chosen using a uniform distribution between the bounds.
* Otherwise, a `Kernel Density Estimator <https://en.wikipedia.org/wiki/Kernel_density_estimation>`_ is fit with the percentage data of the products from the most specific category of the current product that has at least :code:`min_prct_dist_size` defined percentages for this ingredient within the given bounds. This KDE is then used to randomly draw a proportion for the ingredient.

This way of choosing the ingredient proportion to helps to obtain a proportion that is not only possible but also probable.

.. figure:: /_static/ingredients_proportion_choice.svg
    :width: 1000
    :align: center
    :alt: Ingredients proportion choice

    Example with :code:`min_prct_dist_size = 7`