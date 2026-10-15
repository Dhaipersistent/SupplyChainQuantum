import numpy as np
import pytest

from inner_layer.hardware_runner import run_on_ibm_hardware
from inner_layer.warm_start_qaoa import run_warm_start_qaoa


def test_warm_start_qaoa_returns_a_binary_sample_and_metrics():
    matrix = np.array([[1.0, -2.0], [0.0, 1.0]])
    result = run_warm_start_qaoa(
        matrix,
        np.array([1, 0]),
        maxiter=3,
        feasible_validator=lambda _: True,
    )

    assert len(result.bitstring) == 2
    assert set(result.bitstring) <= {0, 1}
    assert result.variable_count == 2
    assert result.backend == "statevector_simulator"
    assert result.feasible
    assert result.runtime_seconds >= 0


def test_hardware_runner_refuses_unvalidated_submission():
    with pytest.raises(RuntimeError, match="simulator validation"):
        run_on_ibm_hardware(
            np.zeros((1, 1)),
            [0],
            parameters=[0.1, 0.2],
            simulator_validated=False,
            explicit_opt_in=True,
        )


def test_hardware_runner_enforces_variable_limit_before_runtime_import():
    with pytest.raises(ValueError, match="at most 20"):
        run_on_ibm_hardware(
            np.zeros((21, 21)),
            [0] * 21,
            parameters=[0.1, 0.2],
            simulator_validated=True,
            explicit_opt_in=True,
        )


def test_hardware_runner_keeps_ibm_submission_disabled():
    with pytest.raises(RuntimeError, match="hardware execution is disabled"):
        run_on_ibm_hardware(
            np.zeros((1, 1)),
            [0],
            parameters=[0.1, 0.2],
            simulator_validated=True,
            explicit_opt_in=True,
        )
