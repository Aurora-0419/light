from app.runtime.backend_selector import (
    choose_perception_backend,
    detect_runtime_capabilities,
)


def test_detect_runtime_capabilities_reports_required_keys():
    capabilities = detect_runtime_capabilities()

    assert set(capabilities) >= {
        "platform",
        "cuda_available",
        "horizon_bpu_available",
        "recommended_backend",
        "warning",
    }


def test_choose_perception_backend_never_defaults_to_cuda_on_rdkx5():
    backend = choose_perception_backend(
        {
            "platform": "rdk_x5",
            "cuda_available": False,
            "horizon_bpu_available": False,
        }
    )

    assert backend["backend"] == "cpu"
    assert "BPU" in backend["warning"]
