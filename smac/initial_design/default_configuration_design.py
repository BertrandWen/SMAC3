from __future__ import annotations

from typing import List

from ConfigSpace import Configuration

from smac.initial_design import InitialDesign

__copyright__ = "Copyright 2022, automl.org"
__license__ = "3-clause BSD"


class DefaultInitialDesign(InitialDesign):
    """Initial design that evaluates default configuration."""

    def _select_configurations(self) -> List[Configuration]:
        """Selects the default configuration.

        Returns
        -------
        config: Configuration
            Initial incumbent configuration.
        """
        config = self.configspace.get_default_configuration()
        config.origin = "Default"
        return [config]
