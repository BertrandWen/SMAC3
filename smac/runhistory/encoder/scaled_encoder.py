from __future__ import annotations

import abc
from typing import List, Mapping, Optional, Tuple

import numpy as np

from smac.runhistory.encoder.encoder import RunHistoryEncoder
from smac import constants
from smac.configspace import convert_configurations_to_array
from smac.model.imputer import AbstractImputer
from smac.multi_objective import AbstractMultiObjectiveAlgorithm
from smac.multi_objective.utils import normalize_costs
from smac.runhistory.runhistory import RunHistory, RunKey, RunValue
from smac.runner.runner import StatusType
from smac.scenario import Scenario
from smac.utils.logging import get_logger

__copyright__ = "Copyright 2022, automl.org"
__license__ = "3-clause BSD"


logger = get_logger(__name__)


class RunHistoryScaledEncoder(RunHistoryEncoder):
    """TODO."""

    def transform_response_values(self, values: np.ndarray) -> np.ndarray:
        """Transform function response values. Transforms the response values by linearly scaling
        them between zero and one.

        Parameters
        ----------
        values : np.ndarray
            Response values to be transformed.

        Returns
        -------
        np.ndarray
        """
        min_y = self.min_y - (self.perc - self.min_y)  # Subtract the difference between the percentile and the minimum
        min_y -= constants.VERY_SMALL_NUMBER  # Minimal value to avoid numerical issues in the log scaling below
        # linear scaling
        # prevent diving by zero

        min_y[np.where(min_y == self.max_y)] *= 1 - 10**-101
        values = (values - min_y) / (self.max_y - min_y)
        return values
