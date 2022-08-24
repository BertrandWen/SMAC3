from __future__ import annotations

from typing import Any, Mapping

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

import ConfigSpace
import numpy as np
from ConfigSpace.read_and_write import json as cs_json

from smac.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Scenario:
    """
    The scenario manages environment variables and therefore gives context in which frame the optimization is performed.

    Parameters
    ----------
    configspace : ConfigSpace
        The configuration space from which to sample the configurations.
    name : str | None, defaults to None
        The name of the run. If no name is passed, SMAC generates a hash from the meta data.
        Specify this argument to identify your run easily.
    output_directory : Path, defaults to Path("smac3_output")
        The directory in which to save the output. The files are saved in `./output_directory/name/seed`.
    deterministic : bool, defaults to False
        If deterministic is set to true, only one seed is passed to the target algorithm.
        Otherwise, multiple seeds (if n_seeds of the intensifier is greater than 1) are passed
        to the target algorithm to ensure generalization.
    objective : str | list[str] | None, defaults to "cost"
        The objective(s) to optimize. This argument is required for multi-objective optimization.
    crash_cost : float | list[float], defaults to np.inf
        Defines the cost for a failed trial. In case of multi-objective, each objective can be associated with
        a different cost.
    termination_cost_threshold : float | list[float], defaults to np.inf
        Defines a cost threshold when the optimization should stop. In case of multi-objective, each objective *must* be
        associated with a different cost. The optimization stops when all objectives crossed the threshold.
    walltime_limit : float, defaults to np.inf
        The maximum time in seconds that SMAC is allowed to run.
    cputime_limit : float, defaults to np.inf
        The maximum CPU time in seconds that SMAC is allowed to run.
    trial_walltime_limit : float | None, defaults to None
        The maximum time in seconds that a trial is allowed to run. If not specified,
        no constraints are enforced. Otherwise, the process will be spawned by pynisher.
    trial_memory_limit : int | None, defaults to None
        The maximum memory in MB that a trial is allowed to use. If not specified,
        no constraints are enforced. Otherwise, the process will be spawned by pynisher.
    n_trials : int, defaults to 100
        The maximum number of trials (combination of configuration, seed, budget, and instance, depending on the task)
        to run.
    instances : list[str] | None, defaults to None
        Names of the instances to use. If None, no instances are used.
        Instances could be dataset names, seeds, subsets, etc.
    instance_features : dict[str, list[float]] | None, defaults to None
        Instances can be associated with features. For example, meta data of the dataset (mean, var, ...) can be
        incorporated which are then further used to expand the training data of the surrogate model.
    instance_order : str | None, defaults to "shuffle_once"
        How to order the instances. Possible values are "shuffle" and "shuffle_once". You can disable this feature by
        setting the argument to None.
    min_budget : float | None, defaults to None
        The minimum budget (epochs, subset size, number of instances, ...) that is used for the optimization.
        Use this argument if you use multi-fidelity or instance optimization.
    max_budget : float | None, defaults to None
        The maximum budget (epochs, subset size, number of instances, ...) that is used for the optimization.
        Use this argument if you use multi-fidelity or instance optimization.
    seed : int, defaults to 0
        The seed is used to make results reproducible. If seed is -1, SMAC will generate a random seed.
    n_workers : int, defaults to 1
        The number of workers to use for parallelization. If `n_workers` is greather than 1, SMAC will use
        Dask to parallelize the optimization.
    """

    # General
    configspace: ConfigSpace
    name: str | None = None
    output_directory: Path = Path("smac3_output")
    deterministic: bool = False

    # Objectives
    objectives: str | list[str] = "cost"
    crash_cost: float | list[float] = np.inf
    termination_cost_threshold: float | list[float] = np.inf

    # Limitations
    walltime_limit: float = np.inf
    cputime_limit: float = np.inf
    trial_walltime_limit: float | None = None
    trial_memory_limit: int | None = None
    n_trials: int = 100

    # Algorithm Configuration
    instances: list[str] | None = None
    instance_features: dict[str, list[float]] | None = None
    instance_order: str | None = "shuffle_once"

    # Budgets
    min_budget: float | None = None
    max_budget: float | None = None

    # Others
    seed: int = 0
    n_workers: int = 1

    def __post_init__(self) -> None:
        """Checks whether the config is valid."""
        # Use random seed if seed is -1
        if self.seed == -1:
            seed = random.randint(0, 999999)
            object.__setattr__(self, "seed", seed)

        # Assert correct instance order
        assert self.instance_order in ["shuffle", "shuffle_once", None], "Invalid instance order."

        # Change directory wrt name and seed
        self._change_output_directory()

        # Set hashes
        object.__setattr__(self, "_meta", {})

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Scenario):
            # When using __dict__, we make sure to include the meta data
            return self.__dict__ == other.__dict__

        raise RuntimeError("Can only compare scenario objects.")

    def _change_output_directory(self) -> None:
        # Create output directory
        if self.name is not None:
            new = Path(self.name) / str(self.seed)
            if not str(self.output_directory).endswith(str(new)):
                object.__setattr__(self, "output_directory", self.output_directory / new)

    def _set_meta(self, meta: dict[str, dict[str, Any]]) -> None:
        object.__setattr__(self, "_meta", meta)

        # We overwrite name with the hash of the meta (if no name is passed)
        if self.name is None:
            hash = hashlib.md5(str(self.__dict__).encode("utf-8")).hexdigest()
            object.__setattr__(self, "name", hash)
            self._change_output_directory()

    def get_meta(self) -> dict[str, str]:
        """Returns the meta data of the SMAC run.

        Note
        ----
        Meta data are set when the facade is initialized.
        """
        return self._meta

    def count_objectives(self) -> int:
        """Counts the number of objectives."""
        if isinstance(self.objectives, list):
            return len(self.objectives)

        return 1

    def count_instance_features(self) -> int:
        """Counts the number of instance features."""
        # Check whether key of instance features exist
        n_features = 0
        if self.instance_features is not None:
            for k, v in self.instance_features.items():
                if k not in self.instances:
                    raise RuntimeError(f"Instance {k} is not specified in instances.")

                if n_features == 0:
                    n_features = len(v)
                else:
                    if len(v) != n_features:
                        raise RuntimeError("Instances must have the same number of features.")

        return n_features

    def save(self) -> None:
        """Saves internal variables and the configuration space to a file."""
        if self.name is None:
            raise RuntimeError(
                "Please specify meta data for generating a name. Alternatively, you can specify a name manually."
            )

        self.output_directory.mkdir(parents=True, exist_ok=True)

        data = {}
        for k, v in self.__dict__.items():
            if k in ["configspace", "output_directory"]:
                continue

            data[k] = v

        # Convert `output_directory`
        data["output_directory"] = str(self.output_directory)

        # Save everything
        filename = self.output_directory / "scenario.json"
        with open(filename, "w") as fh:
            json.dump(data, fh, indent=4)

        # Save configspace on its own
        configspace_filename = self.output_directory / "configspace.json"
        with open(configspace_filename, "w") as f:
            f.write(cs_json.write(self.configspace))

    @staticmethod
    def load(path: Path) -> Scenario:
        """Loads a scenario and the configuration space from a file."""
        filename = path / "scenario.json"
        with open(filename, "r") as fh:
            data = json.load(fh)

        # Convert `output_directory` to path object again
        data["output_directory"] = Path(data["output_directory"])
        meta = data["_meta"]
        del data["_meta"]

        # Read configspace
        configspace_filename = path / "configspace.json"
        with open(configspace_filename, "r") as f:

            configspace = cs_json.read(f.read())

        data["configspace"] = configspace

        scenario = Scenario(**data)
        scenario._set_meta(meta)

        return scenario