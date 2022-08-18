from __future__ import annotations

from typing import Any

from dataclasses import dataclass

from ConfigSpace import Configuration

import smac

__copyright__ = "Copyright 2022, automl.org"
__license__ = "3-clause BSD"


@dataclass(frozen=True)
class InstanceSeedKey:
    instance: str | None = None
    seed: int | None = None


@dataclass(frozen=True)
class InstanceSeedBudgetKey:
    instance: str | None = None
    seed: int | None = None
    budget: float = 0.0

    def __lt__(self, other: InstanceSeedBudgetKey) -> bool:
        return self.budget < other.budget


@dataclass(frozen=True)
class RunKey:
    config_id: int
    instance: str | None = None
    seed: int | None = None
    budget: float = 0.0


@dataclass(frozen=True)
class RunValue:
    cost: float | list[float]
    time: float
    status: smac.runhistory.enumerations.StatusType
    starttime: float
    endtime: float
    additional_info: dict[str, Any]


@dataclass(frozen=True)
class RunInfo:
    config: Configuration
    instance: str | None
    seed: int
    budget: float = 0.0
    source: int = 0
