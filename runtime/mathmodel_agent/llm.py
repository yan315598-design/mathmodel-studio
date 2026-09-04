"""LLM 协议抽象: 客户端接口、统一重试与 LiteLLM 适配。

MockLLM 因 150 行约束拆到 mockllm.py (本模块不 import 它, 避免循环依赖)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Protocol, TypeVar

T = TypeVar("T")

# 命中即视为瞬时错误可重试的关键词 (litellm 各家 provider 异常文案不统一, 按子串匹配)
_TRANSIENT_MARKERS = ("timeout", "timed out", "rate limit", "ratelimit", "429",
                      "connection", "temporarily", "overloaded")


class LLMError(Exception):
    """LLM 调用相关错误基类。"""


class TransientLLMError(LLMError):
    """可重试的瞬时错误 (限流/网络抖动/超时)。"""


class LLMUnavailableError(LLMError):
    """后端不可用, 例如 litellm 未安装。"""


@dataclass
class LLMResponse:
    """一次补全的结构化结果。"""

    text: str
    role: str
    model: str
    usage_tokens: int = 0


class LLMClient(Protocol):
    """runtime 对 LLM 的最小要求: 按角色补全一段 prompt。"""

    def complete(self, role: str, prompt: str) -> LLMResponse: ...


def call_with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    retry_on: tuple[type[BaseException], ...] = (TransientLLMError,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """指数退避重试: 最多 attempts 次, 第 i 次失败后等待 base_delay * 2^i。

    重试耗尽后抛最后一次异常; 非 retry_on 异常立即上抛。
    """
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as exc:  # noqa: PERF203
            last = exc
            if i < attempts - 1:
                sleep(base_delay * (2 ** i))
    assert last is not None
    raise last


def _is_transient(exc: BaseException) -> bool:
    """判断是否可重试的瞬时错误。

    优先读异常的 status_code 属性 (litellm/openai 风格):
    429/408/5xx 重试, 其余 4xx (认证/参数错误) 立即失败;
    无 status_code 时退回异常类型/文案匹配 (尽力而为的归类)。
    """
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status in (408, 429) or 500 <= status < 600
    if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower():
        return True
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


class LiteLLMClient:
    """litellm 适配器; import 延迟到首次调用, 未安装时给清晰指引而非崩溃。"""

    def __init__(self, config, temperature: float = 0.3) -> None:  # noqa: ANN001
        self.config = config
        self.temperature = temperature
        self._litellm = None

    def _backend(self):
        """惰性加载 litellm; 仅真实 LLM 模式才会触发。"""
        if self._litellm is None:
            try:
                import litellm  # 延迟 import: mock 模式零第三方依赖
            except ImportError as exc:
                raise LLMUnavailableError(
                    "litellm 未安装; 请 pip install 'mathmodel-agent[litellm]' (或 pip install litellm),"
                    " 或改用 --mock 模式"
                ) from exc
            self._litellm = litellm
        return self._litellm

    def complete(self, role: str, prompt: str) -> LLMResponse:
        """单轮补全: 模型/key/超时取自 AgentConfig, 瞬时错误走统一重试。"""

        def _once() -> LLMResponse:
            try:
                resp = self._backend().completion(
                    model=self.config.model_for(role),
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.config.api_key_for(role),
                    timeout=self.config.llm_timeout_s,
                    temperature=self.temperature,
                )
            except LLMError:
                raise
            except Exception as exc:
                if _is_transient(exc):
                    raise TransientLLMError(f"{type(exc).__name__}: {exc}") from exc
                raise
            text = resp["choices"][0]["message"]["content"] or ""
            usage = resp.get("usage") or {}
            return LLMResponse(text=str(text), role=role, model=self.config.model_for(role),
                               usage_tokens=int(usage.get("total_tokens") or 0))

        try:
            return call_with_retry(_once, attempts=3, base_delay=1.0)
        except TransientLLMError as exc:
            raise LLMError(f"LiteLLM 重试 3 次仍失败 (role={role}): {exc}") from exc
