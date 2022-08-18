"""
Support Vector Machine with Cross-Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An example of optimizing a simple support vector machine on the IRIS benchmark. We use the hyperparameter optimization 
facade, which uses a random forest as its surrogate model. It is able to scale to higher evaluation budgets and a higher 
number of dimensions. Also, you can use mixed data types as well as conditional hyperparameters by nature.

The hyperparameter facade only supports a single fidelity approach. Therefore, only the configuration (not a budget like
iterations) is passed to the target algorithm.
"""

import numpy as np
from ConfigSpace import Categorical, Configuration, ConfigurationSpace, Float, Integer
from ConfigSpace.conditions import InCondition
from sklearn import datasets, svm
from sklearn.model_selection import cross_val_score

from smac import HyperparameterFacade, Scenario

__copyright__ = "Copyright 2021, AutoML.org Freiburg-Hannover"
__license__ = "3-clause BSD"


# We load the iris-dataset (a widely used benchmark)
iris = datasets.load_iris()


class SVM:
    @property
    def configspace(self):
        # Build Configuration Space which defines all parameters and their ranges
        cs = ConfigurationSpace(seed=0)

        # First we create our hyperparameters
        kernel = Categorical("kernel", ["linear", "poly", "rbf", "sigmoid"], default="poly")
        C = Float("C", (0.001, 1000.0), default=1.0, log=True)
        shrinking = Categorical("shrinking", [True, False], default=True)
        degree = Integer("degree", (1, 5), default=3)
        coef = Float("coef0", (0.0, 10.0), default=0.0)
        gamma = Categorical("gamma", ["auto", "value"], default="auto")
        gamma_value = Float("gamma_value", (0.0001, 8.0), default=1.0, log=True)

        # Then we create dependencies
        use_degree = InCondition(child=degree, parent=kernel, values=["poly"])
        use_coef = InCondition(child=coef, parent=kernel, values=["poly", "sigmoid"])
        use_gamma = InCondition(child=gamma, parent=kernel, values=["rbf", "poly", "sigmoid"])
        use_gamma_value = InCondition(child=gamma_value, parent=gamma, values=["value"])

        # Add hyperparameters and conditions to our configspace
        cs.add_hyperparameters([kernel, C, shrinking, degree, coef, gamma, gamma_value])
        cs.add_conditions([use_degree, use_coef, use_gamma, use_gamma_value])

        return cs

    def train(self, config: Configuration, seed: int = 0) -> float:
        """Creates a SVM based on a configuration and evaluates it on the
        iris-dataset using cross-validation."""
        config_dict = config.get_dictionary()
        if "gamma" in config:
            config_dict["gamma"] = config_dict["gamma_value"] if config_dict["gamma"] == "value" else "auto"
            config_dict.pop("gamma_value", None)

        classifier = svm.SVC(**config_dict, random_state=seed)
        scores = cross_val_score(classifier, iris.data, iris.target, cv=5)
        cost = 1 - np.mean(scores)

        return cost


if __name__ == "__main__":
    classifier = SVM()
    configspace = classifier.configspace
    default_config = configspace.get_default_configuration()

    # Example call of the target algorithm
    default_value = classifier.train(default_config)
    print(f"Default value: {round(default_value, 2)}")

    # Next, we create an object, holding general information about the run
    scenario = Scenario(
        configspace,
        n_trials=50,  # We want 50 target algorithm evaluations
    )

    # We want to run only five initial configurations
    initial_design = HyperparameterFacade.get_initial_design(scenario, n_configs=5)

    # Now we use SMAC to find the best hyperparameters
    smac = HyperparameterFacade(
        scenario,
        classifier.train,
        initial_design=initial_design,
        overwrite=False,  # If the run exists, we do not overwrite it
    )

    incumbent = smac.optimize()
    incumbent_value = classifier.train(incumbent)
    print(f"Incumbent value: {round(incumbent_value, 2)}")