Estimating product impact
=========================

The estimating the environmental impact of an Open Food Facts product can be done using the This equation is implemented by :class:`~impacts_estimation.impact_estimation.ImpactEstimator` or the wrappers :class:`~impacts_estimation.impact_estimation.estimate_impacts` and :class:`~impacts_estimation.impact_estimation.estimate_impacts_safe`. The later can be used in case of failure to progressively relax the constraints on the model in order to get a result.

General principle
-----------------

Central limit theorem
+++++++++++++++++++++

This algorithm uses a Monte-Carlo based approach to estimate the expectation of a random variable by a large number of draws. It uses the `Central Limit Theorem <https://en.wikipedia.org/wiki/Central_limit_theorem>`_ which establishes the convergence in law of the mean of a sequence of random variables to a normal distribution in order to detect when the number of computed values is sufficient.

This theorem can be stated as follows:
    Let :math:`(X_n), n \in \mathbb{N^*}` be a sequence of independent random variables of the same distribution, with expectation :math:`\mu` and finite variance :math:`\sigma^2`.
    Let :math:`\overline{X}_n` be the mean of the :math:`n` first samples.

    .. math::
        \forall n \in \mathbb{N^*}, \overline{X}_n = \frac{X_1+\dots+X_n}{n}

    The law of :math:`\overline{X}_n` converges to a normal law :math:`\mathcal{N}\left(\mu,\frac{\sigma}{\sqrt{n}}\right)`.

This theorem could be used to calculate the expectation of the environmental impact of a recipe obtained with :class:`~impacts_estimation.impact_estimation.RandomRecipeCreator`. However, the calculated impact values have a large dispersion, sometimes over several orders of magnitude, and seem to follow a lognormal distribution. In this case, the geometric mean of the distribution is a more relevant indicator than the arithmetic mean. However, the geometric mean can be calculated as the exponential of the arithmetic mean of the logarithms of the values.

.. math::
    \forall n \in \mathbb{N^*}, G=\exp\left(\frac{\sum_{i=1}^{n}{\ln(x_i)}}{n}\right)

Thus, we can apply the CLT by considering the logarithm of the environmental impact of a recipe as a random variable :math:`(X_n)` of expectation :math:`\mu` and variance :math:`\sigma^2`.
Thus, the mean :math:`\overline{X}_n` of a large number of draws of this random variable converges in law to a normal distribution of the same expectation :math:`\mu` and whose standard deviation :math:`\frac{\sigma}{\sqrt{n}}` decreases as the number of draws :math:`n` increases.
Since the variance :math:`\sigma^2` of the impact of the compositions is unknown, we can use a Student's law to calculate a confidence interval of the expectation :math:`\mu`. Once this confidence interval is sufficiently narrowed, one can consider that the number of draws is sufficient to calculate a result. We then calculate the geometric mean of the draws :math:`G`
as the exponential of the mean of the logarithms.

.. math::
    G=\exp(\overline{X}_n)

Confidence score weighting
++++++++++++++++++++++++++

In order to give more weight to the most credible compositions in the calculation of the final result, the confidence score was used to weight the calculation of the averages. The result of the algorithm is the weighted geometric mean :math:`G'` defined by :

.. math::
    G'=\exp\left(\frac{\sum_{i=1}^{n}{w_i\cdot\ln(x_i)}}{\sum_{i=1}^{n}w_i}\right)

The advantage of this weighting is that it makes the result more credible by minimizing the weight of compositions that are too unlikely. On the other hand, the classical version of the CLT does not apply to weighted averages. Indeed, one of the conditions of applicability of the CLT is that the random variables must be independent, and we can consider a weighted average as an average for which the draws appear as many times as their weight, which makes them dependent.
However, one can intuitively think that the weighting of the draws does not prevent the convergence of the result. One could even think that it accelerates it by hypothesizing that the higher the confidence score of a recipe the closer its impact value is to the average.

Algorithm description
+++++++++++++++++++++

The algorithm consists of a while loop that continues as long as the minimum number of loop turns is not reached or the confidence interval of the result of at least one of the impact categories is higher than the stopping threshold.
At each turn of this loop, :meth:`~impacts_estimation.impact_estimation.RandomRecipeCreator.random_recipe` is called to obtain a possible recipe of the product and its confidence score is calculated.
We then loop over all the impact categories considered to calculate the impact of this recipe and add it to a list.
The logarithms of the impact values of the recipes calculated so far are averaged and weighted by their confidence score and this result is added to a list.
This list thus contains the weighted average of the impact logs of the first :math:`1, 2, \dots, n` first draws.
Thanks to the CLT, we know that the values of this list of means follow a normal distribution.
We can therefore estimate a confidence interval for this distribution.
If the width of this interval converted back to the linear space (by taking the exponential of the bounds) is smaller than the ``confidence_interval_width`` parameter for all impact categories, the loop ends and the weighted geometric mean of the calculated impacts for each category is returned.
