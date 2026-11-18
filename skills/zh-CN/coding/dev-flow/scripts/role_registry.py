#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


INHERIT = "inherit"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROLES_PATH = Path("assets/roles.json")
REQUIRED_STAGES = (
    "SOLO",
    "TASK-02",
    "TASK-03",
    "CODE-REVIEW",
    "TASK-04",
    "TASK-05",
    "SUMMARY",
)
VALID_CONTEXT_MODES = {"isolated", "inherit"}
VALID_ON_SPAWN_ERROR = {"inherit", "fail"}
ROLE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class RegistryError(ValueError):
    pass


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"角色注册表不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"角色注册表不是有效 JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistryError("角色注册表顶层必须是 JSON 对象")
    return value


def validate_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{field} 必须是非空字符串")
    return value.strip()


def validate_prompt_path(value, package_root: Path) -> tuple[str, Path]:
    prompt_value = validate_text(value, "prompt")
    prompt_path = Path(prompt_value)
    if prompt_path.is_absolute():
        raise RegistryError(f"prompt 必须是相对技能包根目录的路径: {prompt_value}")
    resolved_root = package_root.resolve()
    resolved_prompt = (resolved_root / prompt_path).resolve()
    try:
        resolved_prompt.relative_to(resolved_root)
    except ValueError as exc:
        raise RegistryError(f"prompt 不能跳出技能包根目录: {prompt_value}") from exc
    if not resolved_prompt.is_file() or resolved_prompt.stat().st_size == 0:
        raise RegistryError(f"prompt 文件不存在或为空: {prompt_value}")
    return prompt_value, resolved_prompt


def resolve_settings(raw_defaults: dict, raw_role: dict) -> dict:
    if raw_defaults is None:
        raw_defaults = {}
    if not isinstance(raw_defaults, dict):
        raise RegistryError("defaults 必须是 JSON 对象")
    if not isinstance(raw_role, dict):
        raise RegistryError("角色定义必须是 JSON 对象")

    settings = {
        "model": INHERIT,
        "reasoning_effort": INHERIT,
        "context_mode": "isolated",
        "on_spawn_error": "inherit",
        "spawnable": True,
    }
    settings.update(raw_defaults)
    for key in (
        "model",
        "reasoning_effort",
        "context_mode",
        "on_spawn_error",
    ):
        if key in raw_role:
            settings[key] = raw_role[key]

    settings["model"] = validate_text(settings["model"], "model")
    settings["reasoning_effort"] = validate_text(
        settings["reasoning_effort"], "reasoning_effort"
    )
    if settings["context_mode"] not in VALID_CONTEXT_MODES:
        raise RegistryError("context_mode 只能是 isolated 或 inherit")
    if settings["on_spawn_error"] not in VALID_ON_SPAWN_ERROR:
        raise RegistryError("on_spawn_error 只能是 inherit 或 fail")
    if not isinstance(settings["spawnable"], bool):
        raise RegistryError("spawnable 必须是布尔值")

    model_overridden = settings["model"] != INHERIT
    effort_overridden = settings["reasoning_effort"] != INHERIT
    if (model_overridden or effort_overridden) and settings["context_mode"] != "isolated":
        raise RegistryError("设置 model 或 reasoning_effort 时必须使用 isolated 上下文")

    settings["model_override"] = model_overridden
    settings["reasoning_effort_override"] = effort_overridden
    return settings


def load_model_profiles(data: dict) -> dict:
    raw_profiles = data.get("model_profiles", {})
    if not isinstance(raw_profiles, dict):
        raise RegistryError("model_profiles 必须是 JSON 对象")

    profiles = {}
    for model, raw_profile in raw_profiles.items():
        model_name = validate_text(model, "model_profiles key")
        if not isinstance(raw_profile, dict):
            raise RegistryError(f"model_profiles.{model_name} 必须是 JSON 对象")
        efforts = raw_profile.get("reasoning_efforts")
        if not isinstance(efforts, list) or not efforts:
            raise RegistryError(
                f"model_profiles.{model_name}.reasoning_efforts 必须是非空数组"
            )
        normalized_efforts = []
        for effort in efforts:
            normalized_efforts.append(
                validate_text(
                    effort,
                    f"model_profiles.{model_name}.reasoning_efforts[]",
                )
            )
        fallback = raw_profile.get("fallback_reasoning_effort")
        if fallback is not None:
            fallback = validate_text(
                fallback,
                f"model_profiles.{model_name}.fallback_reasoning_effort",
            )
            if fallback not in normalized_efforts:
                raise RegistryError(
                    f"model_profiles.{model_name}.fallback_reasoning_effort "
                    "必须包含在 reasoning_efforts 中"
                )
        profiles[model_name] = {
            "reasoning_efforts": normalized_efforts,
            "fallback_reasoning_effort": fallback,
        }
    return profiles


def model_compatibility(model: str, reasoning_effort: str, profiles: dict) -> dict:
    if model == INHERIT or reasoning_effort == INHERIT or model not in profiles:
        return {
            "profile": profiles.get(model),
            "compatible": True,
            "suggested_reasoning_effort": None,
        }
    profile = profiles[model]
    compatible = reasoning_effort in profile["reasoning_efforts"]
    return {
        "profile": profile,
        "compatible": compatible,
        "suggested_reasoning_effort": (
            None if compatible else profile.get("fallback_reasoning_effort")
        ),
    }


def load_registry(package_root: Path, roles_path: Path) -> tuple[dict, dict, dict]:
    data = read_json(roles_path)
    version = validate_text(data.get("version"), "version")
    if version != "1.0":
        raise RegistryError(f"不支持的 roles.json 版本: {version}")
    defaults = resolve_settings(data.get("defaults", {}), {})
    model_profiles = load_model_profiles(data)
    raw_roles = data.get("roles")
    if not isinstance(raw_roles, dict) or not raw_roles:
        raise RegistryError("roles 必须是非空 JSON 对象")

    normalized = {}
    stages = {}
    for role_id, raw_role in raw_roles.items():
        if not isinstance(role_id, str) or not ROLE_ID_PATTERN.fullmatch(role_id):
            raise RegistryError(f"角色 ID 不合法: {role_id!r}")
        settings = resolve_settings(data.get("defaults", {}), raw_role)
        stage = validate_text(raw_role.get("stage"), f"{role_id}.stage")
        if stage not in REQUIRED_STAGES:
            raise RegistryError(f"{role_id}.stage 不是已知阶段: {stage}")
        if stage in stages:
            raise RegistryError(
                f"阶段 {stage} 同时映射到角色 {stages[stage]} 和 {role_id}"
            )
        stages[stage] = role_id
        prompt_relative, prompt_path = validate_prompt_path(
            raw_role.get("prompt"), package_root
        )
        compatibility = model_compatibility(
            settings["model"],
            settings["reasoning_effort"],
            model_profiles,
        )
        if settings["model"] != INHERIT and not compatibility["compatible"]:
            raise RegistryError(
                f"{role_id} 的模型 {settings['model']} 不支持 "
                f"reasoning_effort={settings['reasoning_effort']}；"
                f"建议 {compatibility['suggested_reasoning_effort'] or '使用受支持档位'}"
            )
        normalized[role_id] = {
            "role_id": role_id,
            "stage": stage,
            "prompt": str(prompt_path),
            "prompt_relative": prompt_relative,
            "spawnable": settings["spawnable"],
            "model": settings["model"],
            "reasoning_effort": settings["reasoning_effort"],
            "context_mode": settings["context_mode"],
            "on_spawn_error": settings["on_spawn_error"],
            "model_override": settings["model_override"],
            "reasoning_effort_override": settings["reasoning_effort_override"],
            "model_source": (
                "role"
                if raw_role.get("model", INHERIT) != INHERIT
                else ("defaults" if defaults["model"] != INHERIT else "parent")
            ),
            "reasoning_effort_source": (
                "role"
                if raw_role.get("reasoning_effort", INHERIT) != INHERIT
                else (
                    "defaults"
                    if defaults["reasoning_effort"] != INHERIT
                    else "parent"
                )
            ),
            "model_profile": model_profiles.get(settings["model"]),
            "model_compatibility": compatibility,
        }

    missing = [stage for stage in REQUIRED_STAGES if stage not in stages]
    if missing:
        raise RegistryError("缺少阶段角色: " + ", ".join(missing))
    return normalized, defaults, model_profiles


def find_role(registry: dict, target: str) -> dict:
    if target in registry:
        return registry[target]
    for role in registry.values():
        if role["stage"] == target:
            return role
    raise RegistryError(f"找不到角色或阶段: {target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="解析和校验 DevFlow 角色注册表")
    parser.add_argument(
        "--root",
        type=Path,
        default=PACKAGE_ROOT,
        help="技能包根目录，默认从脚本位置推断",
    )
    parser.add_argument(
        "--roles",
        type=Path,
        default=None,
        help="角色注册表路径，默认 {root}/assets/roles.json",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="校验角色注册表")
    resolve = subparsers.add_parser("resolve", help="解析角色 ID 或阶段")
    resolve.add_argument("target")
    check_model = subparsers.add_parser("check-model", help="检查模型与推理档兼容性")
    check_model.add_argument("--model", required=True)
    check_model.add_argument("--reasoning-effort", required=True)
    subparsers.add_parser("list", help="列出阶段与角色映射")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    package_root = args.root.resolve()
    roles_path = args.roles or (package_root / DEFAULT_ROLES_PATH)
    if not roles_path.is_absolute():
        roles_path = package_root / roles_path
    try:
        registry, _defaults, model_profiles = load_registry(package_root, roles_path)
        if args.command == "validate":
            print(f"roles.json: valid ({len(registry)} roles)")
            return 0
        if args.command == "resolve":
            print(json.dumps(find_role(registry, args.target), ensure_ascii=False, indent=2))
            return 0
        if args.command == "check-model":
            result = model_compatibility(
                args.model,
                args.reasoning_effort,
                model_profiles,
            )
            print(
                json.dumps(
                    {
                        "model": args.model,
                        "reasoning_effort": args.reasoning_effort,
                        **result,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0 if result["compatible"] else 1
        if args.command == "list":
            mapping = {
                role["stage"]: role["role_id"]
                for role in sorted(registry.values(), key=lambda item: item["stage"])
            }
            print(json.dumps(mapping, ensure_ascii=False, indent=2))
            return 0
    except RegistryError as exc:
        print(f"role_registry: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
