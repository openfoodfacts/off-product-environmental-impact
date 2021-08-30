# Analysis of performance

This README is a work in progress, and currently mostly contains data received from @GustaveCoste about previous analysis.

## Datasets

A dataset containing a compatible version of each compound product in AgriBalyse was created.

In [test_dataset_nutri_calculated.json](test_dataset_nutri_calculated.json) the CIQUAL nutritional composition of the ingredients was used
to compute a nutritional table for each product, and then the ingredients and nutritional table was
used to compute environmental impacts.

In [test_dataset_nutri_from_ciqual.json](test_dataset_nutri_from_ciqual.json) the CIQUAL nutritional composition of the compound product itself was used, to get an unbiased (from this codebase) nutritional table, and then the ingredients and nutritional table was used to compute environmental impacts.

## Visualizations

![Computed vs reference EF impact with self-computed nutrient tables](pef_median_vs_agri_calc.png "Computed vs reference EF impat with self-computed nutrient tables")

