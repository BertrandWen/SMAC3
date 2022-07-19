from __future__ import annotations
from typing import Any, List

import numpy as np
from ConfigSpace.hyperparameters import FloatHyperparameter

from smac.acquisition_function import AbstractAcquisitionFunction


class PriorAcquisitionFunction(AbstractAcquisitionFunction):
    r"""Weight the acquisition function with a user-defined prior over the optimum.

    See "PiBO: Augmenting Acquisition Functions with User Beliefs for Bayesian Optimization" by Carl
    Hvarfner et al. (###nolinkyet###) for further details.
    """

    def __init__(
        self,
        acquisition_function: AbstractAcquisitionFunction,
        decay_beta: float,
        prior_floor: float = 1e-12,
        discretize: bool = False,
        discrete_bins_factor: float = 10.0,
        **kwargs: Any,
    ):
        """Constructor

        Parameters
        ----------
        decay_beta: Decay factor on the user prior - defaults to n_iterations / 10 if not specifed
            otherwise.
        prior_floor : Lowest possible value of the prior, to ensure non-negativity for all values
            in the search space.
        discretize : Whether to discretize (bin) the densities for continous parameters. Triggered
            for Random Forest models and continous hyperparameters to avoid a pathological case
            where all Random Forest randomness is removed (RF surrogates require piecewise constant
            acquisition functions to be well-behaved)
        discrete_bins_factor : If discretizing, the multiple on the number of allowed bins for
            each parameter

        kwargs
            Additional keyword arguments
        """
        super().__init__()
        self.long_name = "Prior Acquisition Function (%s)" % acquisition_function.__class__.__name__
        self.acq = acquisition_function
        self._functions = []  # type: List[AbstractAcquisitionFunction]
        self.eta = None

        # Problem here: We don't have our model at the init rn
        raise RuntimeError(":(")

        self.hyperparameters = self.model.get_configspace().get_hyperparameters_dict()
        self.decay_beta = decay_beta
        self.prior_floor = prior_floor
        self.discretize = discretize
        if self.discretize:
            self.discrete_bins_factor = discrete_bins_factor

        # check if the acquisition function is LCB or TS - then the acquisition function values
        # need to be rescaled to assure positiveness & correct magnitude
        if isinstance(self.acq, IntegratedAcquisitionFunction):
            acquisition_type = self.acq.acq
        else:
            acquisition_type = self.acq

        self.rescale_acq = isinstance(acquisition_type, (LCB, TS))
        self.iteration_number = 0

    def update(self, **kwargs: Any) -> None:
        """Update the acquisition function attributes required for calculation.

        Updates the model, the accompanying acquisition function and tracks the iteration number.

        Parameters
        ----------
        kwargs
            Additional keyword arguments
        """
        self.iteration_number += 1
        self.acq.update(**kwargs)
        self.eta = kwargs.get("eta")

    def _compute_prior(self, X: np.ndarray) -> np.ndarray:
        """Computes the prior-weighted acquisition function values, where the prior on each
        parameter is multiplied by a decay factor controlled by the parameter decay_beta and
        the iteration number. Multivariate priors are not supported, for now.

        Parameters
        ----------
        X: np.ndarray(N, D), The input points where the user-specified prior
            should be evaluated. The dimensionality of X is (N, D), with N as
            the number of points to evaluate at and D is the number of
            dimensions of one X.

        Returns
        -------
        np.ndarray(N,1)
            The user prior over the optimum for values of X
        """
        prior_values = np.ones((len(X), 1))
        # iterate over the hyperparmeters (alphabetically sorted) and the columns, which come
        # in the same order
        for parameter, X_col in zip(self.hyperparameters.values(), X.T):
            if self.discretize and isinstance(parameter, FloatHyperparameter):
                number_of_bins = int(np.ceil(self.discrete_bins_factor * self.decay_beta / self.iteration_number))
                prior_values *= self._compute_discretized_pdf(parameter, X_col, number_of_bins) + self.prior_floor
            else:
                prior_values *= parameter._pdf(X_col[:, np.newaxis])

        return prior_values

    def _compute_discretized_pdf(
        self, parameter: FloatHyperparameter, X_col: np.ndarray, number_of_bins: int
    ) -> np.ndarray:
        """Discretizes (bins) prior values on continous a specific continous parameter
        to an increasingly coarse discretization determined by the prior decay parameter.

        Parameters
        ----------
        parameter: a FloatHyperparameter that, due to using a random forest
            surrogate, must have its prior discretized
        X_col: np.ndarray(N, ), The input points where the acquisition function
            should be evaluated. The dimensionality of X is (N, ), with N as
            the number of points to evaluate for the specific hyperparameter
        number_of_bins: The number of unique values allowed on the
            discretized version of the pdf.

        Returns
        -------
        np.ndarray(N,1)
            The user prior over the optimum for the parameter at hand.
        """
        # evaluates the actual pdf on all the relevant points
        pdf_values = parameter._pdf(X_col[:, np.newaxis])
        # retrieves the largest value of the pdf in the domain
        lower, upper = (0, parameter.get_max_density())
        # creates the bins (the possible discrete options of the pdf)
        bin_values = np.linspace(lower, upper, number_of_bins)
        # generates an index (bin) for each evaluated point
        bin_indices = np.clip(
            np.round((pdf_values - lower) * number_of_bins / (upper - lower)), 0, number_of_bins - 1
        ).astype(int)
        # gets the actual value for each point
        prior_values = bin_values[bin_indices]
        return prior_values

    def _compute(self, X: np.ndarray) -> np.ndarray:
        """Computes the prior-weighted acquisition function values, where the prior on each
        parameter is multiplied by a decay factor controlled by the parameter decay_beta and
        the iteration number. Multivariate priors are not supported, for now.

        Parameters
        ----------
        X: np.ndarray(N, D), The input points where the acquisition function
            should be evaluated. The dimensionality of X is (N, D), with N as
            the number of points to evaluate at and D is the number of
            dimensions of one X.

        Returns
        -------
        np.ndarray(N,1)
            Prior-weighted acquisition function values of X
        """
        if self.rescale_acq:
            # for TS and UCB, we need to scale the function values to not run into issues
            # of negative values or issues of varying magnitudes (here, they are both)
            # negative by design and just flipping the sign leads to picking the worst point)
            acq_values = np.clip(self.acq._compute(X) + self.eta, 0, np.inf)
        else:
            acq_values = self.acq._compute(X)
        prior_values = self._compute_prior(X) + self.prior_floor
        decayed_prior_values = np.power(prior_values, self.decay_beta / self.iteration_number)

        return acq_values * decayed_prior_values
