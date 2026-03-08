"""NDJSON stream emitter for --output-format stream-json."""

import json
import sys


class StreamEmitter:
    """Emits NDJSON events to stdout for stream-json output format."""

    def emit(self, event: dict):
        line = json.dumps(event, separators=(",", ":"))
        print(line, file=sys.stdout, flush=True)

    def system_init(self, model: str, plugins: list[str]):
        self.emit({
            "type": "system",
            "subtype": "init",
            "message": "session started",
            "model": model,
            "plugins": plugins,
        })

    def system_done(self, iterations: int):
        self.emit({
            "type": "system",
            "subtype": "done",
            "message": "task complete",
            "iterations": iterations,
        })

    def system_error(self, message: str):
        self.emit({
            "type": "system",
            "subtype": "error",
            "message": message,
        })

    def assistant(self, content_blocks: list[dict]):
        self.emit({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": content_blocks,
            },
        })

    def tool_use(self, tool_id: str, name: str, input_args: dict):
        self.emit({
            "type": "tool_use",
            "name": name,
            "id": tool_id,
            "input": input_args,
        })

    def tool_result(self, tool_id: str, name: str, output: str, error: bool = False):
        self.emit({
            "type": "tool_result",
            "id": tool_id,
            "name": name,
            "output": output,
            "error": error,
        })

    def result(self, text: str, is_error: bool, duration_ms: int, iterations: int):
        self.emit({
            "type": "result",
            "result": text,
            "is_error": is_error,
            "duration_ms": duration_ms,
            "iterations": iterations,
        })
