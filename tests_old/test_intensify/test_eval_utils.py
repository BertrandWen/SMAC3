from smac.runhistory.runhistory import RunHistory, RunInfo
from smac.utils.stats import Stats
from smac.runner.target_algorithm_runner import TargetAlgorithmRunner

__copyright__ = "Copyright 2021, AutoML.org Freiburg-Hannover"
__license__ = "3-clause BSD"


def eval_challenger(
    run_info: RunInfo,
    taf: TargetAlgorithmRunner,
    stats: Stats,
    runhistory: RunHistory,
    force_update=False,
):
    """
    Wrapper over challenger evaluation

    SMBO objects handles run history now, but to keep
    same testing functionality this function is a small
    wrapper to launch the taf and add it to the history
    """
    # evaluating configuration
    run_info, result = taf.run_wrapper(
        run_info=run_info,
    )

    stats.ta_time_used += float(result.time)
    runhistory.add(
        config=run_info.config,
        cost=result.cost,
        time=result.time,
        status=result.status,
        instance_id=run_info.instance,
        seed=run_info.seed,
        budget=run_info.budget,
        force_update=force_update,
    )
    stats.n_configs = len(runhistory.config_ids)
    return result
