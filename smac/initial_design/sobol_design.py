from __future__ import annotations

from typing import List

import warnings

from ConfigSpace.configuration_space import Configuration
from ConfigSpace.hyperparameters import Constant
from scipy.stats.qmc import Sobol

from smac.initial_design.initial_design import InitialDesign
from smac.scenario import Scenario

__copyright__ = "Copyright 2022, automl.org"
__license__ = "3-clause BSD"


class SobolInitialDesign(InitialDesign):
    """Sobol sequence design with a scrambled Sobol sequence.

    See https://scipy.github.io/devdocs/reference/generated/scipy.stats.qmc.Sobol.html for further information

    Attributes
    ----------
    configs : List[Configuration]
        List of configurations to be evaluated
        Don't pass configs to the constructor;
        otherwise factorial design is overwritten
    """

    def __init__(
        self,
        scenario: Scenario,
        configs: list[Configuration] | None = None,
        n_configs_per_hyperparameter: int | None = 10,
        max_config_ratio: float = 0.25,
        n_configs: int | None = None,
        seed: int | None = None,
    ):
        if len(scenario.configspace.get_hyperparameters()) > 21201:
            raise ValueError(
                'The default initial design "Sobol sequence" can only handle up to 21201 dimensions. '
                'Please use a different initial design, such as the "Latin Hypercube design".',
            )

        super().__init__(
            scenario,
            configs,
            n_configs_per_hyperparameter,
            max_config_ratio,
            n_configs,
            seed,
        )

    def _select_configurations(self) -> List[Configuration]:
        """Selects a single configuration to run.

        Returns
        -------
        config: Configuration
            initial incumbent configuration
        """
        params = self.configspace.get_hyperparameters()

        constants = 0
        for p in params:
            if isinstance(p, Constant):
                constants += 1

        dim = len(params) - constants
        sobol_gen = Sobol(d=dim, scramble=True, seed=self.rng.randint(low=0, high=10000000))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sobol = sobol_gen.random(self.n_configs)

        return self._transform_continuous_designs(
            design=sobol, origin="Sobol Initial Design", configspace=self.configspace
        )
