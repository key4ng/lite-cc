"""LLM client — wraps litellm.completion() with OCI auth support."""

import json
from dataclasses import dataclass, field

import litellm
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


def _patch_oci_config():
    """Patch OCIChatConfig for max_completion_tokens support."""
    try:
        from litellm.llms.oci.chat.transformation import OCIChatConfig
        _orig_init = OCIChatConfig.__init__
        def _patched_init(self):
            _orig_init(self)
            self.openai_to_oci_generic_param_map["max_tokens"] = False
            self.openai_to_oci_generic_param_map["max_completion_tokens"] = "max_completion_tokens"
        OCIChatConfig.__init__ = _patched_init
    except (ImportError, AttributeError):
        pass


_patch_oci_config()


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self._oci_signer = None

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
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
            if self._oci_signer is None:
                self._oci_signer = _get_oci_signer(self.config)
            kwargs["oci_signer"] = self._oci_signer
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
            # reasoning tokens may be in completion_tokens_details
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
