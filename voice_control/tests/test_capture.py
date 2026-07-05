from pathlib import Path

from app.audio.capture import AudioCaptureConfig, build_arecord_command


def test_build_arecord_command_uses_expected_parameters(tmp_path: Path):
    output = tmp_path / "sample.wav"
    config = AudioCaptureConfig(device="plughw:0,0", rate=16000, channels=1, duration_seconds=2)

    command = build_arecord_command(config, output)

    assert command[:2] == ["arecord", "-D"]
    assert "plughw:0,0" in command
    assert "16000" in command
    assert command[-1] == str(output)
