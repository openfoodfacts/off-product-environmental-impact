""" Functions used for environmental impact characterization of OFF ingredients """

from math import floor, ceil
import numpy as np

# Warning: Value for score of 5 for Reliability, Completeness and Geographical correlation are not given in the
#  reference paper. It has been linearly interpolated.
gsd_from_score = {'Reliability': {1: 1,
                                  2: 1.54,
                                  3: 1.61,
                                  4: 1.69,
                                  5: 1.77},
                  'Completeness': {1: 1,
                                   2: 1.03,
                                   3: 1.04,
                                   4: 1.08,
                                   5: 1.12},
                  'Temporal correlation': {1: 1,
                                           2: 1.03,
                                           3: 1.10,
                                           4: 1.19,
                                           5: 1.29},
                  'Geographical correlation': {1: 1,
                                               2: 1.04,
                                               3: 1.08,
                                               4: 1.11,
                                               5: 1.15},
                  'Further technological correlation': {1: 1,
                                                        2: 1.18,
                                                        3: 1.65,
                                                        4: 2.08,
                                                        5: 2.80}}


def gsd_from_dqr(precision, temp_repr, geo_repr, tech_repr):
    """
    Compute an impact geometric standard deviation (GSD) from a Data Quality Rating (DQR) to be used as parameter of a
        log-normal uncertainty distribution.

    References:
        Ciroth, A., Muller, S., Weidema, B. et al.
        Empirically based uncertainty factors for the pedigree matrix in ecoinvent.
        Int J Life Cycle Assess 21, 1338–1348 (2016).
        https://doi.org/10.1007/s11367-013-0670-5

        Product Environmental Footprint Category Rules Guidance
        https://ec.europa.eu/environment/eussd/smgp/pdf/PEFCR_guidance_v6.3.pdf

    Args:
        precision (float): Precision attribute of the DQR
        temp_repr (float):
        geo_repr (float):
        tech_repr (float):

    Returns:
        float: Tuple constituted by the geometric mean and geometric standard deviation of a log-normal
            uncertainty distribution

    Examples:
        >>> gsd_from_dqr(precision=1.4, temp_repr=2.3, geo_repr=2.6, tech_repr=1.5)
        1.4999781381939195
    """

    # Precision is added twice because it is supposed to correspond to both reliability and completeness
    pedigree = {'Reliability': float(precision),
                'Completeness': float(precision),
                'Temporal correlation': float(temp_repr),
                'Geographical correlation': float(geo_repr),
                'Further technological correlation': float(tech_repr)}

    gsd = 1
    for category, score in pedigree.items():
        # As the score is not necessarily an integer and may be between the bounds given by Ciroth et al. 2016,
        #  the resulting GSD is linearly interpolated
        score_min, score_max = floor(score), ceil(score)
        gsd_min, gsd_max = gsd_from_score[category][score_min], gsd_from_score[category][score_max]
        x = [score_min, score_max]
        y = [gsd_min, gsd_max]
        interpolated_gsd = np.interp(score, x, y)

        gsd *= interpolated_gsd

    return float(gsd)
