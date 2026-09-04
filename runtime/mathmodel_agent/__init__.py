"""mathmodel-agent: mathmodel-studio 的薄 agent runtime 原型。

skill (SKILL.md + references/ + scripts/) 是大脑, 本包只是执行器:
驱动 stage 流程、调用 skill 脚本、执行代码、持久化 state。
"""

from .config import AgentConfig
from .llm import LLMClient, LLMResponse, LiteLLMClient
from .loop import StageDriver
from .mockllm import MockLLM
from .state import DecisionLog

__version__ = "0.1.0"

__all__ = [
    "AgentConfig", "DecisionLog", "LLMClient", "LLMResponse",
    "LiteLLMClient", "MockLLM", "StageDriver", "__version__",
]
