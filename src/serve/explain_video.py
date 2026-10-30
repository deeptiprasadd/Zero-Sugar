"""Task 12.6 - the three explanations ("drivers") the tool may show, exactly as fixed in D-060.

Only the Instagram content model (model B of D-047), only its three stable features (D-048): hashtags, share of the
video with talking, share of frames with a face. Same method as D-047: `shap.LinearExplainer` on the served model's
own imputed and scaled inputs, the 120 Instagram training videos as the background, all of them (`max_samples` set).

For each feature the page shows this video's value beside the average of the 120 (the SHAP reference point) and the
model's position with and without that difference. A feature that was not measured is "not known" and not explained;
a feature whose sign in the served model differs from the stable direction is not explained (D-060).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DRIVERS = ["hashtag_count", "talk_dur_frac", "face_present_frac"]
STABLE_SIGN = {"hashtag_count": 1.0, "talk_dur_frac": 1.0, "face_present_frac": 1.0}   # D-048: more -> higher


def _explainer(model, background: np.ndarray):
    import shap
    return shap.LinearExplainer(model.named_steps["m"], shap.maskers.Independent(background, max_samples=len(background)))


class _Formula:
    """What shap's LinearExplainer returns for a linear model: coefficient x (value - background mean). The build step
    proves the two equal (`shap_linear_check`, D-060); the online demo (D-066) has no shap and uses this."""

    def __init__(self, model, background: np.ndarray):
        m = model.named_steps["m"]
        self.coef, self.mean = m.coef_[0], background.mean(axis=0)
        self.expected_value = float(self.coef @ self.mean + m.intercept_[0])

    def shap_values(self, z):
        return self.coef * (np.asarray(z, float) - self.mean)


def _explainer_for(model, background: np.ndarray):
    try:
        return _explainer(model, background)
    except ImportError:
        return _Formula(model, background)


def linear_check(model, background: np.ndarray) -> float:
    """Largest gap between shap's values and coefficient x (z - background mean) on the background itself."""
    sv = np.asarray(_explainer(model, background).shap_values(background))
    coef = model.named_steps["m"].coef_[0]
    return float(np.max(np.abs(sv - coef * (background - background.mean(axis=0)))))


def explain(X: pd.DataFrame, art: dict) -> dict:
    """The explanations for one Instagram video (X: the 21 inputs in the trained order, missing as NaN)."""
    from src.serve.pipeline import position_of
    schema, model = art["schema"], art["model"]
    order = schema["feature_order"]
    bg = np.asarray(schema["ig_background_z"], float)
    ex = _explainer_for(model, bg)
    z = model[:-1].transform(X[order])
    sv = np.asarray(ex.shap_values(z))[0]
    margin = float(model.named_steps["m"].decision_function(z)[0])
    base = float(np.ravel(ex.expected_value)[0])
    if abs(sv.sum() + base - margin) > 1e-6:
        raise RuntimeError("explanation does not add up to the model's score (D-060 additivity check)")
    sigmoid = lambda t: 1.0 / (1.0 + np.exp(-t))  # noqa: E731
    pos_with = position_of(art, sigmoid(margin))
    means = model.named_steps["sc"].mean_
    out = []
    for f in DRIVERS:
        j = order.index(f)
        raw = X[f].iloc[0]
        item = {"feature": f, "value": None if pd.isna(raw) else float(raw), "average_of_120": float(means[j])}
        if pd.isna(raw):
            item["status"] = "not known"
        elif not schema["driver_sign_agrees"][f]:
            item["status"] = "not explained: the served model does not agree with the stable direction"
        else:
            item.update({"status": "explained", "shap_log_odds": float(sv[j]),
                         "model_scores_it": "higher" if sv[j] > 0 else ("lower" if sv[j] < 0 else "no differently"),
                         "position_with": pos_with, "position_at_average": position_of(art, sigmoid(margin - sv[j]))})
        out.append(item)
    others = float(sv.sum() - sum(sv[order.index(f)] for f in DRIVERS))
    return {"drivers": out, "position": pos_with, "other_18_log_odds": others}
