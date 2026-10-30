"""The base-rate arithmetic the pages need (D-053/D-054), kept apart from the model fitting in build_models.py so
the online demo can use it without loading the fitting libraries (D-066)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def design(platform: pd.Series, log_f: pd.Series) -> np.ndarray:
    return np.column_stack([np.ones(len(platform)), (platform == "instagram").astype(float).to_numpy(),
                            log_f.to_numpy(float)])


def base_predict(b: dict, platform: pd.Series, log_f: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    x = design(platform, log_f)
    mean = x @ b["beta"]
    var_fixed = np.einsum("ij,jk,ik->i", x, b["cov"], x)
    sd = np.sqrt(var_fixed + b["var_account"] + b["var_resid"])
    return mean, sd
