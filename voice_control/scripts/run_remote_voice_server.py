from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import serve

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.interaction import VoiceInteractionSession
from app.runtime.remote import (
    RemoteRecognitionSession,
    build_ready_message,
    build_result_message,
    parse_client_hello,
)
from app.speech.vosk_bridge import VoskStreamingRecognizer


def load_config() -> dict:
    return yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8")) or {}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run remote voice websocket server")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    return parser


def make_remote_session(config: dict) -> RemoteRecognitionSession:
    audio = config.get("audio", {})
    speech = config.get("speech", {})
    recognizer = VoskStreamingRecognizer(
        ROOT / str(speech.get("model_path", "models/vosk-model-small-cn")),
        sample_rate=int(audio.get("rate", 16000)),
    )
    return RemoteRecognitionSession(
        recognizer=recognizer,
        interaction_session=VoiceInteractionSession(
            wake_phrase=str(speech.get("wake_phrase", "你好小灯")),
            command_window_seconds=4.0,
            command_window_delay_seconds=float(speech.get("command_window_delay_seconds", 2.0)),
        ),
    )


def handle_connection(websocket) -> None:
    remote_address = getattr(websocket, "remote_address", None)
    print(f"remote voice client accepted: {remote_address}", flush=True)
    try:
        config = load_config()
        session = make_remote_session(config)
        hello = parse_client_hello(str(websocket.recv(timeout=5.0)))
        print(f"remote voice client connected: {remote_address} rate={hello.get('rate')} channels={hello.get('channels')}", flush=True)
        websocket.send(build_ready_message())
        while True:
            message = websocket.recv()
            if isinstance(message, str):
                payload = json.loads(message)
                if payload.get("type") == "close":
                    break
                continue
            result = session.process_audio_chunk(bytes(message))
            if result is not None:
                websocket.send(build_result_message(result))
    except ConnectionClosed:
        print(f"remote voice client disconnected: {remote_address}", flush=True)
        return
    except Exception as exc:
        print(f"remote voice client failed: {remote_address} error={exc}", flush=True)
        return


def main() -> int:
    args = build_arg_parser().parse_args()
    config = load_config()
    remote = config.get("remote", {})
    host = args.host or str(remote.get("host", "0.0.0.0"))
    port = args.port or int(remote.get("port", 8765))
    with serve(handle_connection, host, port):
        print(f"remote voice server listening on ws://{host}:{port}", flush=True)
        try:
            import threading

            threading.Event().wait()
        except KeyboardInterrupt:
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
