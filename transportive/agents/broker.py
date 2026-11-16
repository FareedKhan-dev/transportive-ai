"""agents/broker.py: both models, one credit cap."""
import json
import time

import anthropic
import openai

from ..config import CODER, CREDITS as C, MODELS, VLLM_URL

claude, vllm = anthropic.Anthropic(), openai.OpenAI(base_url=VLLM_URL, api_key="local")


class Session:
    def __init__(self, system, tools, meter, coder=CODER):
        self.coder, self.system, self.meter, self.history, self.tools = coder, system, meter, [], tools
        if coder == "qwen":
            self.history.append({"role": "system", "content": system})

    def turn(self, content):
        if self.meter["credits"] >= self.meter["cap"]:              # checked before every call
            raise RuntimeError(f"credit cap reached on {self.meter['ticket']}")
        return self.opus(content) if self.coder == "opus" else self.qwen(content)

    def opus(self, content):
        if isinstance(content, list):
            content = [{"type": "tool_result", "tool_use_id": i, "content": r} for i, r in content]
        self.history.append({"role": "user", "content": content})
        tools = [{"name": t["name"], "description": t["about"], "input_schema": t["schema"]} for t in self.tools]
        # effort high, the pack cached for later turns
        msg = claude.messages.create(model=MODELS["opus"], max_tokens=16000, system=self.system, messages=self.history,
                                     output_config={"effort": "high"}, cache_control={"type": "ephemeral"},
                                     **({"tools": tools} if tools else {}))
        self.history.append({"role": "assistant", "content": msg.content})
        u = msg.usage
        self.meter["credits"] += (u.input_tokens * C["opus_in_mtok"] + u.output_tokens * C["opus_out_mtok"]
                                  + (u.cache_read_input_tokens or 0) * C["opus_cache_read_mtok"]
                                  + (u.cache_creation_input_tokens or 0) * C["opus_cache_write_mtok"]) / 1e6
        self.meter["refusals"] += msg.stop_reason == "refusal"
        return ("".join(b.text for b in msg.content if b.type == "text"),
                [(b.id, b.name, b.input) for b in msg.content if b.type == "tool_use"])

    def qwen(self, content):
        if isinstance(content, list):
            self.history += [{"role": "tool", "tool_call_id": i, "content": r} for i, r in content]
        else:
            self.history.append({"role": "user", "content": content})
        tools = [{"type": "function", "function": {"name": t["name"], "description": t["about"], "parameters": t["schema"]}}
                 for t in self.tools]
        start = time.monotonic()
        msg = vllm.chat.completions.create(model=MODELS["qwen"], messages=self.history,
                                           **({"tools": tools} if tools else {})).choices[0].message
        self.meter["credits"] += (time.monotonic() - start) / 3600 * C["h100_hour"]   # GPU time while the request runs
        calls = msg.tool_calls or []
        self.history.append({"role": "assistant", "content": msg.content or "",
                             **({"tool_calls": [c.model_dump() for c in calls]} if calls else {})})
        return msg.content or "", [(c.id, c.function.name, json.loads(c.function.arguments)) for c in calls]
