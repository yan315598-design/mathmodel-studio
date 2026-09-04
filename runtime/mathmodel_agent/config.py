"""AgentConfig: 角色→模型映射、API key 解析与模式 token 预算。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 四档角色: 信息抽取 / 建模求解 / 论文写作 / 评审把关
ROLES = ("extraction", "solving", "writing", "review")

# 角色 -> litellm 模型串默认值 (可用 MATHMODEL_MODEL_<ROLE> 覆盖)
DEFAULT_ROLE_MODELS = {
    "extraction": "openai/gpt-4o-mini",
    "solving": "openai/gpt-4o",
    "writing": "openai/gpt-4o",
    "review": "openai/o3-mini",
}

# mode -> 全程 token 预算上限 (对齐 decision_log.budget.tokens_cap 口径)
MODE_TOKEN_BUDGETS = {"fast": 60_000, "standard": 200_000, "championship": 500_000}


@dataclass
class AgentConfig:
    """runtime 全局配置。

    skill_root: mathmodel-studio 仓库根目录, scripts/ 与 references/ 的定位基准。
    role_models: 角色 -> litellm 模型串。
    api_keys: 角色 -> API key; 取值回退顺序为 角色级 env > 全局 MATHMODEL_LLM_API_KEY。
    """

    skill_root: Path
    mode: str = "standard"
    role_models: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ROLE_MODELS))
    api_keys: dict[str, str | None] = field(default_factory=dict)
    llm_timeout_s: float = 120.0
    tool_timeout_s: float = 300.0

    def model_for(self, role: str) -> str:
        """返回角色对应的模型串; 未注册角色抛 KeyError。"""
        return self.role_models[role]

    def api_key_for(self, role: str) -> str | None:
        """角色级 key 优先 (MATHMODEL_LLM_API_KEY_<ROLE>), 回退全局 MATHMODEL_LLM_API_KEY。"""
        return self.api_keys.get(role) or os.environ.get("MATHMODEL_LLM_API_KEY")

    @property
    def token_budget(self) -> int:
        """mode 对应的 token 预算; 未知 mode 抛 KeyError。"""
        return MODE_TOKEN_BUDGETS[self.mode]

    @classmethod
    def from_env(
        cls,
        skill_root: Path,
        mode: str = "standard",
        llm_timeout_s: float = 120.0,
        tool_timeout_s: float = 300.0,
    ) -> "AgentConfig":
        """从环境变量构建配置: MATHMODEL_MODEL_<ROLE> 与 MATHMODEL_LLM_API_KEY(_<ROLE>)。"""
        if mode not in MODE_TOKEN_BUDGETS:
            raise ValueError(f"未知 mode: {mode!r}, 可选 {sorted(MODE_TOKEN_BUDGETS)}")
        role_models = dict(DEFAULT_ROLE_MODELS)
        api_keys: dict[str, str | None] = {}
        for role in ROLES:
            env_model = os.environ.get(f"MATHMODEL_MODEL_{role.upper()}")
            if env_model:
                role_models[role] = env_model
            api_keys[role] = os.environ.get(f"MATHMODEL_LLM_API_KEY_{role.upper()}")
        return cls(
            skill_root=Path(skill_root),
            mode=mode,
            role_models=role_models,
            api_keys=api_keys,
            llm_timeout_s=llm_timeout_s,
            tool_timeout_s=tool_timeout_s,
        )
