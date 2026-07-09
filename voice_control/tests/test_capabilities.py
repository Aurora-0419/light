from app.runtime.capabilities import detect_voice_capabilities


def test_detect_voice_capabilities_reports_required_keys():
    capabilities = detect_voice_capabilities()

    assert set(capabilities) >= {
        "platform",
        "microphone_available",
        "vosk_available",
        "tts_available",
        "recommended_mode",
        "warning",
    }


def test_detect_voice_capabilities_prefers_local_mode_on_rdkx5():
    capabilities = detect_voice_capabilities(
        platform_name="rdk_x5",
        microphone_available=True,
        vosk_available=False,
        tts_available=False,
    )

    assert capabilities["recommended_mode"] == "local_command"
    assert "offline" in capabilities["warning"].lower()
