Result report
=============

In order to make the presentation of the results easier, a reporting tool has been developed. It uses the `Jinja <https://jinja.palletsprojects.com/en/2.11.x/>`_ package to fill an HTML template. The class :class:`~reporting.reporting.ProductImpactReport` is responsible of generating the HTML page that can then be saved using :meth:`~reporting.reporting.ProductImpactReport.to_html`. Figures are saved in SVG files and embedded in an ``<svg>`` tag.

