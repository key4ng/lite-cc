"""LLM client — wraps litellm.completion() with OCI Responses API and fallback."""

import json
from dataclasses import dataclass, field

import litellm
import requests
from cc.config import Config

litellm.drop_params = True


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Usage = field(default_factory=Usage)
    raw: object = None


def _get_oci_signer(config: Config):
    """Create OCI SecurityTokenSigner from config profile."""
    import oci
    import oci.auth.signers
    oci_config = oci.config.from_file("~/.oci/config", config.oci_config_profile)
    with open(oci_config["security_token_file"]) as f:
        token = f.read()
    private_key = oci.signer.load_private_key_from_file(oci_config["key_file"])
    return oci.auth.signers.SecurityTokenSigner(token, private_key)


# --- Responses API helpers ---

def _convert_tools_to_responses_format(tools: list[dict]) -> list[dict]:
    """Convert OpenAI chat tools to Responses API format.

    Chat: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
    Responses: {"type": "function", "name": ..., "description": ..., "parameters": ...}
    """
    result = []
    for tool in tools:
        if tool.get("type") == "function" and "function" in tool:
            fn = tool["function"]
            result.append({
                "type": "function",
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            })
        else:
            result.append(tool)
    return result


def _convert_messages_to_responses_input(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert OpenAI chat messages to Responses API input format.

    Returns (system_instructions, input_items).
    """
    system_parts = []
    input_items = []

    for msg in messages:
        role = msg.get("role")

        if role == "system":
            system_parts.append(msg["content"])

        elif role == "user":
            input_items.append({
                "type": "message",
                "role": "user",
                "content": msg["content"],
            })

        elif role == "assistant":
            if msg.get("content"):
                input_items.append({
                    "type": "message",
                    "role": "assistant",
                    "content": msg["content"],
                })
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                input_items.append({
                    "type": "function_call",
                    "id": tc["id"] + "_fc",
                    "call_id": tc["id"],
                    "name": fn.get("name", ""),
                    "arguments": fn.get("arguments", "{}"),
                })

        elif role == "tool":
            input_items.append({
                "type": "function_call_output",
                "call_id": msg["tool_call_id"],
                "output": msg.get("content", ""),
            })

    return "\n\n".join(system_parts), input_items


def _parse_responses_api_result(data: dict) -> LLMResponse:
    """Parse Responses API JSON into LLMResponse."""
    text_parts = []
    tool_calls = []

    for item in data.get("output", []):
        item_type = item.get("type")

        if item_type == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    text_parts.append(block["text"])

        elif item_type == "function_call":
            args = item.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            tool_calls.append(ToolCall(
                id=item.get("call_id", item["id"]),
                name=item["name"],
                arguments=args,
            ))

    usage = Usage()
    u = data.get("usage", {})
    usage.input_tokens = u.get("input_tokens", 0)
    usage.output_tokens = u.get("output_tokens", 0)
    details = u.get("output_tokens_details", {})
    usage.reasoning_tokens = details.get("reasoning_tokens", 0)

    status = data.get("status", "completed")
    finish = "stop" if status == "completed" else status

    return LLMResponse(
        text="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls,
        finish_reason=finish,
        usage=usage,
        raw=data,
    )


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self._oci_signer = None

    def _ensure_oci_signer(self):
        if self._oci_signer is None:
            self._oci_signer = _get_oci_signer(self.config)
        return self._oci_signer

    def _use_responses_api(self) -> bool:
        """Use Responses API for OCI xai.* and openai.* models."""
        if not self.config.model.startswith("oci/"):
            return False
        model_name = self.config.model[4:]
        return model_name.startswith(("xai.", "openai."))

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        if self._use_responses_api():
            return self._chat_responses_api(messages, tools)
        return self._chat_completions(messages, tools)

    def _chat_responses_api(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """Call OCI GenAI Responses API directly."""
        if not self.config.oci_compartment:
            raise ValueError(
                "OCI compartment ID is required for oci/ models. "
                "Set CC_OCI_COMPARTMENT env var or oci_compartment in ~/.cc/config.yaml"
            )

        signer = self._ensure_oci_signer()
        model_name = self.config.model[4:]  # strip "oci/"
        system_instructions, input_items = _convert_messages_to_responses_input(messages)

        body = {
            "model": model_name,
            "input": input_items,
        }
        if system_instructions:
            body["instructions"] = system_instructions
        if tools:
            body["tools"] = _convert_tools_to_responses_format(tools)

        url = (
            f"https://inference.generativeai.{self.config.oci_region}"
            f".oci.oraclecloud.com/20231130/actions/v1/responses"
        )

        req = requests.Request(
            "POST", url, json=body,
            headers={
                "Content-Type": "application/json",
                "opc-compartment-id": self.config.oci_compartment,
            },
        )
        prepared = req.prepare()
        signer(prepared)

        resp = requests.Session().send(prepared)
        if resp.status_code != 200:
            try:
                err_msg = resp.json().get("message", resp.text[:500])
            except Exception:
                err_msg = resp.text[:500] if resp.text else "(empty response)"
            raise RuntimeError(f"OCI Responses API error {resp.status_code}: {err_msg}")

        return _parse_responses_api_result(resp.json())

    def _chat_completions(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """Fallback: call via litellm.completion() for non-Responses-API models."""
        kwargs = {
            "model": self.config.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        if self.config.model.startswith("oci/"):
            if not self.config.oci_compartment:
                raise ValueError(
                    "OCI compartment ID is required for oci/ models. "
                    "Set CC_OCI_COMPARTMENT env var or oci_compartment in ~/.cc/config.yaml"
                )
            kwargs["oci_signer"] = self._ensure_oci_signer()
            kwargs["oci_region"] = self.config.oci_region
            kwargs["oci_compartment_id"] = self.config.oci_compartment

        response = litellm.completion(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))

        usage = Usage()
        if hasattr(response, "usage") and response.usage:
            u = response.usage
            usage.input_tokens = getattr(u, "prompt_tokens", 0) or 0
            usage.output_tokens = getattr(u, "completion_tokens", 0) or 0
            details = getattr(u, "completion_tokens_details", None)
            if details:
                usage.reasoning_tokens = getattr(details, "reasoning_tokens", 0) or 0

        return LLMResponse(
            text=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            raw=response,
        )
