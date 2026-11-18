#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from role_registry import RegistryError, find_role, load_registry


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACTS = SKILL_ROOT / "assets" / "stage-contracts.json"
DEFAULT_TEMPLATE = SKILL_ROOT / "assets" / "workflow-state-template.json"
DEFAULT_ROLES = SKILL_ROOT / "assets" / "roles.json"
SCRIPT_PATH = Path(__file__).resolve()
STATE_VERSION = "2.0"
VALID_STAGE_STATUS = {
    "pending",
    "in_progress",
    "completed",
    "passed",
    "failed",
    "blocked",
    "cancelled",
    "skipped",
}
VALID_RESULT_STATUS = {"passed", "failed", "blocked"}
VALID_CHECK_RESULTS = {"passed", "failed", "not-run", "blocked"}
VALID_ERROR_CLASSES = {
    "artifact_invalid",
    "scope_violation",
    "provider_error",
    "model_capability_error",
    "test_failed",
    "review_rejected",
    "user_gate",
    "agent_runtime_error",
    "unknown",
}
REQUIRED_RESULT_FIELDS = {
    "stage",
    "role_id",
    "status",
    "artifacts",
    "checks",
    "risks",
    "last_error",
}
ALLOWED_RESULT_FIELDS = REQUIRED_RESULT_FIELDS | {
    "files_changed",
    "api_docs_required",
    "review_result",
    "summary",
    "error_class",
}
RETRYABLE_ERROR_CLASSES = {
    "artifact_invalid",
    "provider_error",
    "model_capability_error",
    "test_failed",
    "review_rejected",
    "agent_runtime_error",
}
STAGE_DEPENDENCIES = {
    "SOLO": [],
    "TASK-01": [],
    "TASK-02": ["TASK-01"],
    "TASK-03": ["TASK-02"],
    "CODE-REVIEW": ["TASK-03"],
    "TASK-04": ["CODE-REVIEW"],
    "TASK-05": ["TASK-04"],
    "SUMMARY": ["TASK-05"],
}
PLACEHOLDER_PATTERN = re.compile(
    r"(\{\{[^}]+\}\}|<TASK_SLUG>|<TASK_ID>|<PT_ID>|"
    r"\bTODO\b|\bTBD\b|PLACEHOLDER|待填写)"
)
SLUG_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class WorkflowError(ValueError):
    pass


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"JSON 无法解析: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"JSON 顶层必须是对象: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(str(temporary), str(path))


def load_contracts(path: Path) -> dict:
    data = read_json(path)
    if data.get("version") != "1.0":
        raise WorkflowError("stage-contracts.json version 必须为 1.0")
    stages = data.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise WorkflowError("stage-contracts.json 缺少 stages")
    for stage, contract in stages.items():
        if not isinstance(contract, dict):
            raise WorkflowError(f"阶段契约必须是对象: {stage}")
        if not isinstance(contract.get("role_id"), str):
            raise WorkflowError(f"{stage}.role_id 缺失")
        if not isinstance(contract.get("artifacts"), list):
            raise WorkflowError(f"{stage}.artifacts 必须是数组")
    return data


def load_state(path: Path) -> dict:
    state = read_json(path)
    version = state.get("version")
    if version != STATE_VERSION:
        raise WorkflowError(f"不支持的状态版本 {version!r}，仅支持 {STATE_VERSION}")
    for field in ("task_slug", "workspace_root", "artifacts_dir", "stages"):
        if not state.get(field):
            raise WorkflowError(f"workflow-state.json 缺少 {field}")
    return state


def save_state(path: Path, state: dict) -> None:
    state["updated_at"] = utc_now()
    write_json(path, state)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def format_path(template: str, state: dict) -> Path:
    artifacts_dir = Path(state["artifacts_dir"]).resolve()
    project_root = Path(state["workspace_root"]).resolve()
    rendered = template.format(
        artifacts_dir=str(artifacts_dir),
        artifacts_root=str(artifacts_dir.parent),
        project_root=str(project_root),
        task_slug=state["task_slug"],
    )
    path = Path(rendered)
    if not path.is_absolute():
        path = artifacts_dir / path
    return path.resolve()


def relative_to_artifacts(path: Path, state: dict) -> str:
    artifacts_dir = Path(state["artifacts_dir"]).resolve()
    try:
        return str(path.resolve().relative_to(artifacts_dir))
    except ValueError:
        return str(path.resolve())


def stage_state(state: dict, stage: str) -> dict:
    stages = state.get("stages")
    if not isinstance(stages, dict) or stage not in stages:
        raise WorkflowError(f"状态中没有阶段 {stage}")
    return stages[stage]


def append_decision(state: dict, record: dict) -> None:
    decisions = state.setdefault("decisions", [])
    if not isinstance(decisions, list):
        raise WorkflowError("decisions 必须是数组")
    decisions.append({"occurred_at": utc_now(), **record})


def ensure_unique_decisions(state: dict) -> None:
    if not isinstance(state.get("decisions", []), list):
        raise WorkflowError("decisions 必须是数组")


def find_section(text: str, expected: str) -> Optional[str]:
    lines = text.splitlines()
    expected_lower = expected.lower()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if expected_lower in heading.lower():
            content = []
            for following in lines[index + 1 :]:
                if following.strip().startswith("#"):
                    break
                content.append(following)
            return "\n".join(content).strip()
    return None


def check_frontmatter(path: Path, text: str) -> List[str]:
    errors = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"{path}: 缺少 YAML front matter")
        return errors
    try:
        closing = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        errors.append(f"{path}: YAML front matter 没有结束分隔符")
        return errors
    frontmatter = "\n".join(lines[1:closing])
    for key in ("task_id", "stage", "author", "date", "run_mode"):
        if not re.search(rf"(?m)^{re.escape(key)}\s*:\s*\S+", frontmatter):
            errors.append(f"{path}: front matter 缺少 {key}")
    return errors


def validate_markdown(path: Path, spec: dict) -> List[str]:
    errors = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"{path}: 文件不存在"]
    except UnicodeDecodeError as exc:
        return [f"{path}: 不是 UTF-8 文本: {exc}"]
    minimum = int(spec.get("min_chars", 1))
    if len(text.strip()) < minimum:
        errors.append(f"{path}: 内容过短，至少需要 {minimum} 个字符")
    errors.extend(check_frontmatter(path, text))
    for section in spec.get("sections", []):
        if find_section(text, section) is None:
            errors.append(f"{path}: 缺少章节或关键字“{section}”")
    match = PLACEHOLDER_PATTERN.search(text)
    if match:
        errors.append(f"{path}: 发现未填写占位符 {match.group(0)!r}")
    return errors


def artifact_specs(contract: dict, result: Optional[dict]) -> List[dict]:
    specs = []
    for raw_spec in contract.get("artifacts", []):
        spec = dict(raw_spec)
        conditional = spec.get("conditional")
        required = bool(spec.get("required", False))
        if conditional == "api_docs_required":
            required = bool(result and result.get("api_docs_required"))
        spec["effective_required"] = required
        specs.append(spec)
    return specs


def validate_artifact_files(
    contract: dict,
    state: dict,
    result: Optional[dict],
) -> Tuple[List[str], List[Path]]:
    errors = []
    present = []
    for spec in artifact_specs(contract, result):
        path = format_path(spec["path"], state)
        required = spec["effective_required"]
        if not path.exists():
            if required:
                errors.append(f"缺少必需产物: {path}")
            continue
        if not path.is_file():
            errors.append(f"产物不是文件: {path}")
            continue
        present.append(path)
        if spec.get("markdown"):
            errors.extend(validate_markdown(path, spec))
    return errors, present


def parse_execution_plan(text: str) -> Tuple[List[dict], List[str]]:
    errors = []
    match = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S | re.I)
    if not match:
        return [], ["execution-plan.md: 缺少 yaml 代码块"]
    lines = match.group(1).splitlines()
    tasks: List[dict] = []
    current: Optional[dict] = None
    mode: Optional[str] = None

    def start_task() -> dict:
        task = {
            "id": "",
            "title": "",
            "files_whitelist": [],
            "pseudocode": [],
            "acceptance": [],
        }
        tasks.append(task)
        return task

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            if mode == "pseudocode" and current is not None:
                current["pseudocode"].append("")
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 2 and re.match(r"^-\s+id\s*:", stripped):
            current = start_task()
            current["id"] = stripped.split(":", 1)[1].strip()
            mode = None
            continue
        if current is None:
            continue
        if indent == 4 and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "title":
                current["title"] = value
                mode = None
            elif key == "files_whitelist":
                mode = "files_whitelist"
            elif key == "pseudocode":
                mode = "pseudocode"
                if value == "|":
                    continue
                if value:
                    current["pseudocode"].append(value)
            elif key == "acceptance":
                mode = "acceptance"
            else:
                mode = None
            continue
        if indent >= 6 and mode == "files_whitelist" and stripped.startswith("- "):
            current["files_whitelist"].append(stripped[2:].strip())
            continue
        if indent >= 6 and mode == "acceptance" and stripped.startswith("- "):
            current["acceptance"].append(stripped[2:].strip())
            continue
        if indent >= 6 and mode == "pseudocode":
            current["pseudocode"].append(raw[6:] if raw.startswith("      ") else stripped)

    if not tasks:
        errors.append("execution-plan.md: parallel_tasks 中没有 PT")
        return [], errors
    return tasks, errors


def validate_execution_plan(path: Path, state: dict, contract_data: dict) -> Tuple[List[dict], List[str]]:
    errors = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], [f"{path}: 文件不存在"]
    tasks, parse_errors = parse_execution_plan(text)
    errors.extend(parse_errors)
    maximum = int(contract_data.get("max_parallel_sub_developers", 6))
    if len(tasks) > maximum:
        errors.append(f"{path}: PT 数量 {len(tasks)} 超过上限 {maximum}")
    seen_ids = set()
    seen_paths: Dict[Path, str] = {}
    workspace = Path(state["workspace_root"]).resolve()
    artifacts_dir = Path(state["artifacts_dir"]).resolve()
    for index, task in enumerate(tasks, start=1):
        task_id = task.get("id") or f"#{index}"
        if not re.match(r"^PT-[A-Za-z0-9._-]+$", task_id):
            errors.append(f"{path}: 非法 PT ID {task_id!r}")
        if task_id in seen_ids:
            errors.append(f"{path}: PT ID 重复 {task_id}")
        seen_ids.add(task_id)
        if not task.get("title"):
            errors.append(f"{path}: {task_id} 缺少 title")
        pseudocode = [line for line in task.get("pseudocode", []) if line.strip()]
        if len(pseudocode) < 5:
            errors.append(f"{path}: {task_id} 的 pseudocode 少于 5 行")
        if not task.get("acceptance"):
            errors.append(f"{path}: {task_id} 缺少 acceptance")
        whitelist = task.get("files_whitelist", [])
        if not whitelist:
            errors.append(f"{path}: {task_id} 缺少 files_whitelist")
        for raw_path in whitelist:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                errors.append(f"{path}: {task_id} 白名单必须是绝对路径: {raw_path}")
                continue
            resolved = candidate.resolve()
            if not is_within(resolved, workspace):
                errors.append(f"{path}: {task_id} 白名单越出工作区: {raw_path}")
            if is_within(resolved, artifacts_dir):
                errors.append(f"{path}: {task_id} 白名单不能写入 artifacts: {raw_path}")
            if resolved in seen_paths and seen_paths[resolved] != task_id:
                errors.append(
                    f"{path}: 文件白名单重叠: {raw_path} "
                    f"同时属于 {seen_paths[resolved]} 和 {task_id}"
                )
            seen_paths[resolved] = task_id
    return tasks, errors


def normalize_result_ref(reference: str, state: dict) -> Path:
    path = Path(reference)
    if not path.is_absolute():
        path = Path(state["artifacts_dir"]) / path
    return path.resolve()


def validate_stage_result(
    result: dict,
    stage: str,
    contract: dict,
    state: dict,
) -> List[str]:
    errors = []
    missing_fields = sorted(REQUIRED_RESULT_FIELDS - set(result))
    if missing_fields:
        errors.append("stage-result 缺少字段: " + ", ".join(missing_fields))
    unknown_fields = sorted(set(result) - ALLOWED_RESULT_FIELDS)
    if unknown_fields:
        errors.append("stage-result 包含未知字段: " + ", ".join(unknown_fields))
    if result.get("stage") != stage:
        errors.append(f"stage-result.stage 应为 {stage}，实际为 {result.get('stage')!r}")
    if result.get("role_id") != contract["role_id"]:
        errors.append(
            f"stage-result.role_id 应为 {contract['role_id']}，"
            f"实际为 {result.get('role_id')!r}"
        )
    status = result.get("status")
    if status not in VALID_RESULT_STATUS:
        errors.append(f"stage-result.status 非法: {status!r}")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or not all(
        isinstance(item, str) and item.strip() for item in artifacts
    ):
        errors.append("stage-result.artifacts 必须是非空字符串数组")
        artifacts = []
    checks = result.get("checks")
    if not isinstance(checks, list):
        errors.append("stage-result.checks 必须是数组")
        checks = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"stage-result.checks[{index}] 必须是对象")
            continue
        if not check.get("name"):
            errors.append(f"stage-result.checks[{index}] 缺少 name")
        if check.get("result") not in VALID_CHECK_RESULTS:
            errors.append(f"stage-result.checks[{index}] result 非法")
    if status == "passed" and any(
        isinstance(check, dict) and check.get("result") == "failed"
        for check in checks
    ):
        errors.append("stage-result.status=passed 但存在 failed 检查项")
    if status == "passed" and result.get("last_error"):
        errors.append("stage-result.status=passed 时 last_error 必须为 null")
    if status in {"failed", "blocked"} and not result.get("last_error"):
        errors.append("stage-result.status=failed/blocked 时必须提供 last_error")
    risks = result.get("risks")
    if not isinstance(risks, list) or not all(isinstance(item, str) for item in risks):
        errors.append("stage-result.risks 必须是字符串数组")
    if "summary" in result and not isinstance(result.get("summary"), str):
        errors.append("stage-result.summary 必须是字符串")
    error_class = result.get("error_class")
    if error_class is not None and error_class not in VALID_ERROR_CLASSES:
        errors.append(f"stage-result.error_class 非法: {error_class!r}")
    if contract.get("requires_files_changed"):
        files_changed = result.get("files_changed")
        if not isinstance(files_changed, list) or not files_changed:
            errors.append("stage-result.files_changed 必须是非空数组")
    if stage == "CODE-REVIEW":
        review_result = result.get("review_result")
        if review_result not in {"passed", "failed"}:
            errors.append("CODE-REVIEW 的 stage-result.review_result 必须是 passed/failed")
        elif status == "passed" and review_result != "passed":
            errors.append("CODE-REVIEW status=passed 与 review_result 不一致")
        elif status == "failed" and review_result != "failed":
            errors.append("CODE-REVIEW status=failed 与 review_result 不一致")
    listed = {normalize_result_ref(item, state) for item in artifacts}
    allowed_artifacts = {
        format_path(spec["path"], state)
        for spec in artifact_specs(contract, result)
    }
    for artifact_path in listed:
        if artifact_path not in allowed_artifacts:
            errors.append(
                "stage-result.artifacts 包含阶段契约外路径: "
                f"{relative_to_artifacts(artifact_path, state)}"
            )
    for spec in artifact_specs(contract, result):
        if spec["effective_required"]:
            expected = format_path(spec["path"], state)
            if expected not in listed:
                errors.append(
                    f"stage-result.artifacts 未列出必需产物: "
                    f"{relative_to_artifacts(expected, state)}"
                )
    return errors


def validate_acceptance_table(report_path: Path, tasks: List[dict]) -> List[str]:
    errors = []
    try:
        text = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"{report_path}: 文件不存在"]
    table_lines = [
        line for line in text.splitlines() if line.strip().startswith("|")
    ]
    if not table_lines:
        return [f"{report_path}: 缺少 Acceptance 验证表"]
    for task in tasks:
        task_id = task.get("id", "")
        matched = [
            line
            for line in table_lines
            if task_id in line and re.search(r"\bPASS\b", line, re.I)
        ]
        if not matched:
            errors.append(
                f"{report_path}: Acceptance 表缺少 {task_id} 的 PASS 证据行"
            )
    return errors


def validate_plan_scope(
    result: dict,
    tasks: List[dict],
    state: dict,
) -> List[str]:
    errors = []
    allowed = set()
    for task in tasks:
        for raw_path in task.get("files_whitelist", []):
            allowed.add(Path(raw_path).resolve())
    for raw_path in result.get("files_changed", []):
        if not isinstance(raw_path, str):
            errors.append("files_changed 必须只包含字符串路径")
            continue
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = Path(state["workspace_root"]) / candidate
        resolved = candidate.resolve()
        if resolved not in allowed:
            errors.append(f"实际变更文件越出执行计划白名单: {raw_path}")
    return errors


def validate_review_report(path: Path, result: dict) -> List[str]:
    errors = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"{path}: 文件不存在"]
    passed = bool(re.search(r"\bPASSED\b", text, re.I))
    failed = bool(re.search(r"\bFAILED\b", text, re.I))
    expected_passed = result.get("status") == "passed"
    if expected_passed and (not passed or failed):
        errors.append(f"{path}: 审查报告结论与 stage-result passed 不一致")
    if not expected_passed and not failed:
        errors.append(f"{path}: 审查报告缺少 FAILED 结论")
    if expected_passed:
        for section in ("P0", "P1"):
            content = find_section(text, section)
            normalized = re.sub(
                r"[\s`*_\-:：,，.。;；]",
                "",
                (content or ""),
            ).lower()
            if not content:
                errors.append(f"{path}: 缺少 {section} 问题章节")
            elif not normalized.startswith(
                ("无", "none", "n/a", "0", "未发现")
            ):
                errors.append(f"{path}: PASSED 审查的 {section} 章节必须明确为无问题")
    return errors


def validate_dependencies(state: dict, stage: str) -> List[str]:
    errors = []
    for dependency in STAGE_DEPENDENCIES.get(stage, []):
        dependency_state = state.get("stages", {}).get(dependency)
        if not dependency_state or dependency_state.get("status") not in {
            "completed",
            "passed",
        }:
            errors.append(f"{stage} 的前置阶段 {dependency} 尚未完成")
        if dependency == "CODE-REVIEW" and dependency_state:
            if dependency_state.get("review_result") not in {None, "passed"}:
                errors.append("CODE-REVIEW 未通过，不能进入 TASK-04")
    return errors


def validate_state_shape(state: dict) -> List[str]:
    errors = []
    stages = state.get("stages")
    if not isinstance(stages, dict):
        return ["workflow-state.json: stages 必须是对象"]
    current_stage = state.get("current_stage")
    known_stages = set(stages) | {"PHASE-0"}
    if current_stage not in known_stages:
        errors.append(f"workflow-state.json: current_stage 非法 {current_stage!r}")
    last_event = state.get("last_event")
    if isinstance(last_event, str):
        for suffix in ("_in_progress", "_completed", "_passed", "_failed"):
            if last_event.endswith(suffix):
                event_stage = last_event[: -len(suffix)]
                if event_stage in stages and current_stage != event_stage:
                    errors.append(
                        f"workflow-state.json: last_event={last_event} "
                        f"与 current_stage={current_stage} 不一致"
                    )
                break
    for stage, entry in stages.items():
        if not isinstance(entry, dict):
            errors.append(f"workflow-state.json: stages.{stage} 必须是对象")
            continue
        status = entry.get("status")
        if status not in VALID_STAGE_STATUS:
            errors.append(f"workflow-state.json: stages.{stage}.status 非法 {status!r}")
        if status in {"completed", "passed"} and not entry.get("completed_at"):
            errors.append(
                f"workflow-state.json: stages.{stage} 已完成但缺少 completed_at"
            )
        validation = entry.get("validation")
        if validation is not None and not isinstance(validation, dict):
            errors.append(f"workflow-state.json: stages.{stage}.validation 必须是对象")
    if state.get("summary", {}).get("status") == "completed":
        if not state.get("summary", {}).get("report_path"):
            errors.append("workflow-state.json: completed summary 缺少 report_path")
    return errors


def validate_stage(
    state: dict,
    stage: str,
    contracts: dict,
    contracts_path: Path,
    check_dependencies: bool = True,
) -> dict:
    if stage not in contracts["stages"]:
        raise WorkflowError(f"未知阶段 {stage}")
    contract = contracts["stages"][stage]
    errors: List[str] = validate_state_shape(state)
    warnings: List[str] = []
    if state.get("size_class") not in {"small", "medium", "large"}:
        errors.append("size_class 尚未由 Phase 0 classify 设置")
    entry = state.get("stages", {}).get(stage)
    if contract.get("requires_user_confirmation"):
        if not entry or not entry.get("user_confirmed"):
            errors.append(f"{stage} 尚未记录用户需求确认")
    result = None
    result_path = None
    if contract.get("result_path"):
        result_path = format_path(contract["result_path"], state)
        if result_path.exists():
            try:
                result = read_json(result_path)
            except WorkflowError as exc:
                errors.append(str(exc))
        elif contract.get("result_required"):
            errors.append(f"缺少阶段结果: {result_path}")
    artifact_errors, present_artifacts = validate_artifact_files(
        contract, state, result
    )
    errors.extend(artifact_errors)
    if result is not None:
        errors.extend(validate_stage_result(result, stage, contract, state))
    if check_dependencies and stage != "TASK-01":
        errors.extend(validate_dependencies(state, stage))
    for input_ref in contract.get("inputs", []):
        input_path = format_path(input_ref, state)
        if not input_path.exists():
            errors.append(f"缺少上游输入: {input_path}")
    tasks: List[dict] = []
    validators = set(contract.get("validators", []))
    if "execution_plan" in validators:
        plan_path = format_path("02-design/execution-plan.md", state)
        tasks, plan_errors = validate_execution_plan(
            plan_path,
            state,
            contracts,
        )
        errors.extend(plan_errors)
    elif stage in {"TASK-03", "CODE-REVIEW"}:
        plan_path = format_path("02-design/execution-plan.md", state)
        tasks, plan_errors = validate_execution_plan(plan_path, state, contracts)
        errors.extend(plan_errors)
    if "acceptance_table" in validators:
        report_path = format_path("03-code/change-report.md", state)
        errors.extend(validate_acceptance_table(report_path, tasks))
    if "plan_scope" in validators and result is not None:
        errors.extend(validate_plan_scope(result, tasks, state))
    if "api_conditional" in validators and result is not None:
        api_docs = format_path("03-code/api-docs.md", state)
        if result.get("api_docs_required") and not api_docs.exists():
            errors.append(f"API 文档声明为必需，但文件不存在: {api_docs}")
    if "review_report" in validators and result is not None:
        review_path = format_path("03-code/review-report.md", state)
        errors.extend(validate_review_report(review_path, result))
    if "summary" in validators and stage in {"SOLO", "SUMMARY"}:
        if state.get("summary", {}).get("status") not in {"not_started", "completed"}:
            warnings.append("summary.status 当前不是 not_started 或 completed")
    return {
        "stage": stage,
        "contract": str(contracts_path),
        "result_path": str(result_path) if result_path else None,
        "result": result,
        "tasks": tasks,
        "artifacts": [str(path) for path in present_artifacts],
        "errors": errors,
        "warnings": warnings,
        "status": "passed" if not errors else "failed",
    }


def role_settings_for_stage(
    stage: str,
    roles_path: Path,
    model_override: Optional[str],
    effort_override: Optional[str],
) -> dict:
    registry, _defaults, _profiles = load_registry(SKILL_ROOT, roles_path)
    target = next(
        (role for role in registry.values() if role["stage"] == stage),
        None,
    )
    if target is None:
        raise WorkflowError(f"阶段 {stage} 没有可派发角色")
    model = model_override or target["model"]
    effort = effort_override or target["reasoning_effort"]
    model_source = "user" if model_override else target["model_source"]
    effort_source = "user" if effort_override else target["reasoning_effort_source"]
    compatibility = target.get("model_compatibility", {})
    profile = target.get("model_profile")
    if target["model"] != model:
        from role_registry import model_compatibility

        compatibility = model_compatibility(model, effort, _profiles)
        profile = compatibility.get("profile") or _profiles.get(model)
    fallback = False
    if not compatibility.get("compatible", True):
        suggested = compatibility.get("suggested_reasoning_effort")
        if effort_override:
            raise WorkflowError(
                f"模型 {model} 不支持 reasoning_effort={effort}；"
                f"受支持档位: {', '.join(profile['reasoning_efforts']) if profile else '未知'}"
            )
        if not suggested:
            raise WorkflowError(
                f"模型 {model} 不支持 reasoning_effort={effort}，且没有可用 fallback"
            )
        effort = suggested
        effort_source = "capability-fallback"
        fallback = True
    if model != "inherit" and target["context_mode"] != "isolated":
        raise WorkflowError("覆盖模型时必须使用 isolated 上下文")
    return {
        "role_id": target["role_id"],
        "model": model,
        "reasoning_effort": effort,
        "context_mode": target["context_mode"],
        "on_spawn_error": target["on_spawn_error"],
        "model_source": model_source,
        "reasoning_effort_source": effort_source,
        "fallback": fallback,
        "model_profile": profile,
        "model_compatibility": compatibility,
    }


def command_init(args: argparse.Namespace, contracts: dict) -> dict:
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise WorkflowError(f"工作区不存在: {workspace}")
    if not SLUG_PATTERN.fullmatch(args.slug):
        raise WorkflowError("task slug 只能包含字母、数字、点、下划线和连字符")
    artifact_root = (
        Path(args.artifact_root).resolve()
        if args.artifact_root
        else workspace / "artifacts"
    )
    artifacts_dir = artifact_root / args.slug
    state_path = artifacts_dir / "workflow-state.json"
    if artifacts_dir.exists():
        raise WorkflowError(
            f"任务目录已存在，请使用 status/resume 或新的 slug: {artifacts_dir}"
        )
    if state_path.exists():
        raise WorkflowError(f"状态已存在，请使用 status/resume: {state_path}")
    template = read_json(DEFAULT_TEMPLATE)
    now = utc_now()
    template.update(
        {
            "task_id": args.task_id or args.slug,
            "task_slug": args.slug,
            "run_mode": args.run_mode,
            "host_adapter": args.host_adapter,
            "size_class": args.size,
            "current_stage": "PHASE-0",
            "last_event": "workflow_initialized",
            "next_target": "main",
            "workspace_root": str(workspace),
            "artifacts_dir": str(artifacts_dir),
            "created_at": now,
            "updated_at": now,
            "last_transition": {
                "stage": "PHASE-0",
                "result": "initialized",
                "event": "workflow_initialized",
                "next_target": "main",
                "at": now,
            },
            "project_config": {
                "name": workspace.name,
                "default_branch": args.default_branch,
                "coding_standards": args.coding_standards or "",
            },
        }
    )
    for stage, stage_contract in contracts["stages"].items():
        if stage not in template["stages"]:
            template["stages"][stage] = {
                "status": "pending",
                "executor": stage_contract.get("executor"),
                "role_id": stage_contract.get("role_id"),
                "attempt": 0,
                "retry_count": 0,
                "validation": None,
                "artifact_path": None,
                "artifact_paths": [],
                "started_at": None,
                "finished_at": None,
                "completed_at": None,
                "self_check": None,
            }
        stage_entry = template["stages"][stage]
        stage_entry["result_path"] = stage_contract.get("result_path")
    if args.size == "small":
        for stage in template["stages"]:
            if stage != "SOLO":
                template["stages"][stage]["status"] = "skipped"
        template["next_target"] = "solo-developer"
    elif args.size in {"medium", "large"}:
        template["stages"]["SOLO"]["status"] = "skipped"
    template["last_transition"]["next_target"] = template["next_target"]
    append_decision(
        template,
        {
            "kind": "workflow_initialized",
            "size_class": args.size,
            "reason": "workflow.py init",
        },
    )
    directories = [
        "01-requirement",
        "02-design",
        "03-code",
        "04-e2e",
        "05-knowledge",
        "01-solo",
    ]
    for directory in directories:
        (artifacts_dir / directory).mkdir(parents=True, exist_ok=True)
    write_json(state_path, template)
    return {
        "event": "workflow_initialized",
        "state_path": str(state_path),
        "artifacts_dir": str(artifacts_dir),
        "size_class": args.size,
        "next_target": template["next_target"],
    }


def command_classify(args: argparse.Namespace, contracts: dict) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    for stage, entry in state.get("stages", {}).items():
        if entry.get("status") not in {"pending", "skipped"}:
            raise WorkflowError(
                f"已经有阶段开始执行，不能再修改规模判定: {stage}"
            )
    for stage, contract in contracts["stages"].items():
        entry = stage_state(state, stage)
        entry["status"] = "pending"
        entry["result_path"] = contract.get("result_path")
    state["size_class"] = args.size
    state["current_stage"] = "PHASE-0"
    state["last_event"] = "size_classified"
    state["next_target"] = (
        "solo-developer" if args.size == "small" else "main"
    )
    state["last_transition"] = {
        "stage": "PHASE-0",
        "result": "classified",
        "event": "size_classified",
        "next_target": state["next_target"],
        "at": utc_now(),
    }
    state["last_error"] = None
    state["last_error_class"] = None
    if args.size == "small":
        for stage in state["stages"]:
            if stage != "SOLO":
                state["stages"][stage]["status"] = "skipped"
    else:
        state["stages"]["SOLO"]["status"] = "skipped"
    append_decision(
        state,
        {
            "kind": "size_classified",
            "size_class": args.size,
            "reason": args.reason,
        },
    )
    save_state(state_path, state)
    return {
        "event": "size_classified",
        "size_class": args.size,
        "next_target": state["next_target"],
    }


def command_status(args: argparse.Namespace) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    stages = {}
    for stage, entry in state.get("stages", {}).items():
        result_path = entry.get("result_path")
        result_exists = bool(
            result_path
            and format_path(result_path, state).exists()
        )
        artifact_path = entry.get("artifact_path")
        stages[stage] = {
            "status": entry.get("status"),
            "role_id": entry.get("role_id"),
            "retry_count": entry.get("retry_count", 0),
            "attempt": entry.get("attempt", 0),
            "result_exists": result_exists,
            "artifact_path": artifact_path,
            "artifact_exists": bool(
                artifact_path and Path(artifact_path).exists()
            ),
        }
    return {
        "task_slug": state["task_slug"],
        "size_class": state.get("size_class"),
        "current_stage": state.get("current_stage"),
        "last_event": state.get("last_event"),
        "next_target": state.get("next_target"),
        "last_error": state.get("last_error"),
        "last_error_class": state.get("last_error_class"),
        "last_transition": state.get("last_transition"),
        "summary": state.get("summary"),
        "stages": stages,
    }


def command_handoff(args: argparse.Namespace, contracts: dict) -> str:
    state = load_state(Path(args.state).resolve())
    if state.get("size_class") not in {"small", "medium", "large"}:
        raise WorkflowError("请先运行 workflow.py classify 记录 Phase 0 规模判定")
    if args.stage not in contracts["stages"]:
        raise WorkflowError(f"未知阶段 {args.stage}")
    contract = contracts["stages"][args.stage]
    entry = state.get("stages", {}).get(args.stage)
    if entry and entry.get("status") in {"skipped", "cancelled", "completed", "passed"}:
        raise WorkflowError(
            f"{args.stage} 当前状态为 {entry.get('status')}，不能生成执行任务卡"
        )
    dependency_errors = validate_dependencies(state, args.stage)
    if dependency_errors:
        raise WorkflowError("; ".join(dependency_errors))
    if contract["role_id"] == "main":
        settings = {
            "role_id": "main",
            "model": "inherit",
            "reasoning_effort": "inherit",
            "context_mode": "n/a",
        }
    else:
        settings = role_settings_for_stage(
            args.stage,
            DEFAULT_ROLES,
            args.model,
            args.reasoning_effort,
        )
    missing_inputs = []
    for input_ref in contract.get("inputs", []):
        input_path = format_path(input_ref, state)
        if not input_path.exists():
            missing_inputs.append(str(input_path))
    result_path = (
        format_path(contract["result_path"], state)
        if contract.get("result_path")
        else None
    )
    artifact_lines = "\n".join(
        f"- {format_path(spec['path'], state)}"
        + ("（必需）" if spec.get("required") else "（可选/条件）")
        for spec in contract.get("artifacts", [])
    )
    input_lines = "\n".join(
        f"- {format_path(input_ref, state)}"
        for input_ref in contract.get("inputs", [])
    )
    boundary = [
        "- 不得修改 workflow-state.json。",
        "- 不得修改其他阶段产物。",
        (
            "- 完成后填写 result_path，并运行上面的 validate 命令。"
            if result_path
            else "- 完成后运行上面的 validate 命令。"
        ),
    ]
    lines = [
        f"# {args.stage} 阶段任务卡",
        "",
        f"- PROJECT_ROOT: `{state['workspace_root']}`",
        f"- SKILL_DIR: `{SKILL_ROOT}`",
        f"- workflow_state_path: `{args.state}`",
        f"- role_id: `{settings['role_id']}`",
        f"- model: `{settings['model']}`",
        f"- reasoning_effort: `{settings['reasoning_effort']}`",
        f"- context_mode: `{settings['context_mode']}`",
        f"- result_path: `{result_path or '不适用'}`",
        "",
        "## 必需产物",
        artifact_lines or "- 无",
        "",
        *(
            ["## 上游输入", input_lines, ""]
            if input_lines
            else []
        ),
        "## 完成命令",
        "```bash",
        f"python3 {SCRIPT_PATH} validate --state {args.state} --stage {args.stage}",
        "```",
        "",
        "## 边界",
        *boundary,
    ]
    if missing_inputs:
        raise WorkflowError("缺少上游输入: " + ", ".join(missing_inputs))
    output = "\n".join(lines).rstrip() + "\n"
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        return str(output_path)
    return output


def command_record_spawn(args: argparse.Namespace, contracts: dict) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    if state.get("size_class") not in {"small", "medium", "large"}:
        raise WorkflowError("请先运行 workflow.py classify 记录 Phase 0 规模判定")
    if args.stage not in contracts["stages"]:
        raise WorkflowError(f"未知阶段 {args.stage}")
    contract = contracts["stages"][args.stage]
    if contract["role_id"] == "main":
        raise WorkflowError("main 阶段不派发角色 Agent")
    dependency_errors = validate_dependencies(state, args.stage)
    if dependency_errors:
        raise WorkflowError("; ".join(dependency_errors))
    settings = role_settings_for_stage(
        args.stage,
        DEFAULT_ROLES,
        args.model,
        args.reasoning_effort,
    )
    entry = stage_state(state, args.stage)
    if entry.get("status") in {"completed", "passed", "cancelled", "skipped"}:
        raise WorkflowError(
            f"{args.stage} 当前状态为 {entry.get('status')}，不能登记新的 spawn"
        )
    now = utc_now()
    entry.update(
        {
            "status": "in_progress",
            "executor": contract["executor"],
            "role_id": settings["role_id"],
            "host": args.host,
            "agent_handle": args.handle,
            "model": settings["model"],
            "reasoning_effort": settings["reasoning_effort"],
            "context_mode": settings["context_mode"],
            "model_source": settings["model_source"],
            "reasoning_effort_source": settings["reasoning_effort_source"],
            "fallback": settings["fallback"],
            "started_at": entry.get("started_at") or now,
            "finished_at": None,
            "completed_at": None,
            "validation": None,
            "artifact_path": None,
            "artifact_paths": [],
            "self_check": None,
            "attempt": max(
                int(entry.get("attempt", 0)),
                int(entry.get("retry_count", 0)) + 1,
            ),
        }
    )
    if args.fork_turns:
        entry["host_metadata"] = {"fork_turns": args.fork_turns}
    state["current_stage"] = args.stage
    state["last_event"] = f"{args.stage}_in_progress"
    state["next_target"] = settings["role_id"]
    state["last_error"] = None
    state["last_error_class"] = None
    state["last_transition"] = {
        "stage": args.stage,
        "result": "in_progress",
        "event": f"{args.stage}_in_progress",
        "next_target": settings["role_id"],
        "at": now,
    }
    append_decision(
        state,
        {
            "kind": "agent_spawned",
            "host": args.host,
            "stage": args.stage,
            "role_id": settings["role_id"],
            "agent_handle": args.handle,
            "model": settings["model"],
            "reasoning_effort": settings["reasoning_effort"],
            "context_mode": settings["context_mode"],
            "fork_turns": args.fork_turns,
            "model_source": settings["model_source"],
            "reasoning_effort_source": settings["reasoning_effort_source"],
            "fallback": settings["fallback"],
        },
    )
    if settings["fallback"]:
        append_decision(
            state,
            {
                "kind": "role_runtime_fallback",
                "host": args.host,
                "stage": args.stage,
                "role_id": settings["role_id"],
                "model": settings["model"],
                "reasoning_effort": settings["reasoning_effort"],
                "fallback": "compatible_reasoning_effort",
            },
        )
    save_state(state_path, state)
    return {
        "event": f"{args.stage}_in_progress",
        "stage": args.stage,
        "next_target": settings["role_id"],
        "agent_handle": args.handle,
        "model": settings["model"],
        "reasoning_effort": settings["reasoning_effort"],
        "fallback": settings["fallback"],
    }


def command_confirm(args: argparse.Namespace, contracts: dict) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    if state.get("size_class") not in {"small", "medium", "large"}:
        raise WorkflowError("请先运行 workflow.py classify 记录 Phase 0 规模判定")
    stage = args.stage
    if stage not in contracts["stages"]:
        raise WorkflowError(f"未知阶段 {stage}")
    contract = contracts["stages"][stage]
    if not contract.get("requires_user_confirmation"):
        raise WorkflowError(f"{stage} 不接受用户确认门禁")
    if state.get("size_class") == "small":
        raise WorkflowError("small 流程不经过 TASK-01")
    entry = stage_state(state, stage)
    now = utc_now()
    entry["user_confirmed"] = True
    entry["confirmed_at"] = now
    entry["confirmation_note"] = args.note
    if entry.get("status") in {"pending", "skipped"}:
        entry["status"] = "in_progress"
        entry["started_at"] = entry.get("started_at") or now
    state["current_stage"] = stage
    state["last_event"] = f"{stage}_in_progress"
    state["next_target"] = contract["role_id"]
    state["last_transition"] = {
        "stage": stage,
        "result": "in_progress",
        "event": f"{stage}_in_progress",
        "next_target": contract["role_id"],
        "at": now,
    }
    append_decision(
        state,
        {
            "kind": "requirement_confirmed",
            "stage": stage,
            "reason": args.note,
        },
    )
    save_state(state_path, state)
    return {
        "event": "requirement_confirmed",
        "stage": stage,
        "confirmed_at": now,
        "next_target": contract["role_id"],
    }


def command_validate(args: argparse.Namespace, contracts: dict) -> dict:
    state = load_state(Path(args.state).resolve())
    return validate_stage(
        state,
        args.stage,
        contracts,
        DEFAULT_CONTRACTS,
    )


def stage_paths_to_state(
    stage_entry: dict,
    contract: dict,
    state: dict,
    result: Optional[dict],
) -> List[Path]:
    present = []
    for spec in artifact_specs(contract, result):
        path = format_path(spec["path"], state)
        if path.exists():
            present.append(path)
    for key, template in contract.get("state_paths", {}).items():
        path = format_path(template, state)
        if path.exists():
            stage_entry[key] = str(path)
    stage_entry["artifact_paths"] = [str(path) for path in present]
    return present


def command_complete(args: argparse.Namespace, contracts: dict) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    stage = args.stage
    if stage not in contracts["stages"]:
        raise WorkflowError(f"未知阶段 {stage}")
    contract = contracts["stages"][stage]
    max_retries = int(contracts.get("max_retries", 2))
    validation = validate_stage(
        state,
        stage,
        contracts,
        DEFAULT_CONTRACTS,
    )
    if validation["errors"]:
        return {
            "event": f"{stage}_failed",
            "stage": stage,
            "status": "failed",
            "errors": validation["errors"],
            "state_written": False,
        }
    result = validation.get("result")
    if contract.get("result_required") and result is None:
        raise WorkflowError(f"{stage} 缺少 stage-result")
    result_status = result.get("status") if result else "passed"
    if result_status not in VALID_RESULT_STATUS:
        raise WorkflowError(f"{stage} result status 非法")
    entry = stage_state(state, stage)
    now = utc_now()
    passed = result_status == "passed"
    blocked = result_status == "blocked"
    if passed:
        stage_status = "completed"
        event = contract.get("pass_event", f"{stage}_completed")
        next_target = contract["next_on_pass"]
        state["last_error"] = None
        state["last_error_class"] = None
    else:
        stage_status = (
            "blocked"
            if blocked
            else contract.get("failed_stage_status", "failed")
        )
        event = contract.get("fail_event", f"{stage}_failed")
        next_target = "main" if blocked else contract["next_on_fail"]
        state["last_error"] = (
            (result or {}).get("last_error")
            or (result or {}).get("summary")
            or f"{stage} result status={result_status}"
        )
        state["last_error_class"] = (
            (result or {}).get("error_class")
            or (
                "user_gate"
                if blocked
                else ("review_rejected" if stage == "CODE-REVIEW" else "unknown")
            )
        )
        if not blocked:
            entry["retry_count"] = int(entry.get("retry_count", 0)) + 1
            if entry["retry_count"] >= max_retries:
                next_target = "main"
                if stage_status == "failed":
                    stage_status = "blocked"
    entry["status"] = stage_status
    entry["validation"] = {
        "status": "passed",
        "checked_at": now,
        "errors": [],
    }
    entry["finished_at"] = now
    if stage_status == "completed":
        entry["completed_at"] = now
    entry["self_check"] = result_status
    stage_paths_to_state(entry, contract, state, result)
    if stage == "TASK-03":
        entry["api_docs_generated"] = bool(
            result and result.get("api_docs_required")
        )
    if stage == "CODE-REVIEW":
        entry["review_result"] = (
            result.get("review_result")
            if result and result.get("review_result")
            else ("passed" if passed else "failed")
        )
        entry["review_comment"] = (result or {}).get("summary")
    if contract.get("mark_summary") and passed:
        state["summary"] = {
            "status": "completed",
            "report_path": str(format_path("workflow-summary.md", state)),
            "completed_at": now,
        }
    state["current_stage"] = stage
    state["last_event"] = event
    state["next_target"] = next_target
    state["last_transition"] = {
        "stage": stage,
        "result": result_status,
        "event": event,
        "next_target": next_target,
        "at": now,
    }
    append_decision(
        state,
        {
            "kind": "stage_completed" if passed else "stage_failed",
            "stage": stage,
            "role_id": contract["role_id"],
            "result": result_status,
            "next_target": next_target,
        },
    )
    save_state(state_path, state)
    return {
        "event": event,
        "stage": stage,
        "status": result_status,
        "next_target": next_target,
        "artifact_paths": entry.get("artifact_paths", []),
        "state_written": True,
    }


def command_fail(args: argparse.Namespace, contracts: dict) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    stage = args.stage
    if stage not in contracts["stages"]:
        raise WorkflowError(f"未知阶段 {stage}")
    if args.error_class not in VALID_ERROR_CLASSES:
        raise WorkflowError(f"未知 error class: {args.error_class}")
    contract = contracts["stages"][stage]
    max_retries = int(contracts.get("max_retries", 2))
    entry = stage_state(state, stage)
    status = args.status
    if args.error_class in {"scope_violation", "user_gate"}:
        status = "blocked"
    entry["status"] = status
    entry["finished_at"] = utc_now()
    entry["self_check"] = "failed"
    entry["validation"] = {
        "status": "failed" if status == "failed" else "blocked",
        "checked_at": utc_now(),
        "errors": [args.error],
    }
    if args.error_class in RETRYABLE_ERROR_CLASSES:
        entry["retry_count"] = int(entry.get("retry_count", 0)) + 1
    next_target = args.next_target
    if not next_target:
        if args.error_class == "scope_violation":
            next_target = "main"
        elif args.error_class == "user_gate":
            next_target = "main"
        elif args.error_class == "test_failed":
            next_target = "developer"
        elif args.error_class == "review_rejected":
            next_target = "developer"
        elif args.error_class == "unknown":
            next_target = "main"
        else:
            next_target = contract["role_id"]
    if (
        args.error_class in RETRYABLE_ERROR_CLASSES
        and int(entry.get("retry_count", 0)) >= max_retries
    ):
        status = "blocked"
        next_target = "main"
    entry["status"] = status
    entry["validation"]["status"] = "failed" if status == "failed" else "blocked"
    state["current_stage"] = stage
    state["last_event"] = f"{stage}_failed"
    state["next_target"] = next_target
    state["last_error"] = args.error
    state["last_error_class"] = args.error_class
    state["last_transition"] = {
        "stage": stage,
        "result": status,
        "event": f"{stage}_failed",
        "next_target": next_target,
        "at": utc_now(),
    }
    append_decision(
        state,
        {
            "kind": "stage_failed",
            "stage": stage,
            "role_id": contract["role_id"],
            "error_class": args.error_class,
            "next_target": next_target,
            "reason": args.error,
        },
    )
    if args.error_class == "model_capability_error":
        append_decision(
            state,
            {
                "kind": "role_runtime_fallback",
                "stage": stage,
                "role_id": contract["role_id"],
                "fallback": "pending_model_capability_recovery",
                "reason": args.error,
            },
        )
    save_state(state_path, state)
    return {
        "event": f"{stage}_failed",
        "stage": stage,
        "status": status,
        "error_class": args.error_class,
        "next_target": next_target,
        "state_written": True,
    }


def command_abort(args: argparse.Namespace, contracts: dict) -> dict:
    state_path = Path(args.state).resolve()
    state = load_state(state_path)
    stage = args.stage or state.get("current_stage")
    if stage == "PHASE-0":
        entry = None
    elif stage not in state.get("stages", {}):
        raise WorkflowError(f"无法中止未知阶段 {stage!r}")
    else:
        entry = state["stages"][stage]
    now = utc_now()
    if entry is not None:
        entry["status"] = "cancelled"
        entry["finished_at"] = now
        entry["validation"] = {
            "status": "cancelled",
            "checked_at": now,
            "errors": [args.reason],
        }
    state["current_stage"] = stage
    state["last_event"] = "workflow_aborted"
    state["next_target"] = "main"
    state["last_error"] = args.reason
    state["last_error_class"] = "user_gate"
    state["last_transition"] = {
        "stage": stage,
        "result": "cancelled",
        "event": "workflow_aborted",
        "next_target": "main",
        "at": now,
    }
    state["summary"] = {
        "status": "aborted",
        "report_path": state.get("summary", {}).get("report_path"),
        "completed_at": None,
    }
    append_decision(
        state,
        {
            "kind": "workflow_aborted",
            "stage": stage,
            "reason": args.reason,
        },
    )
    save_state(state_path, state)
    return {
        "event": "workflow_aborted",
        "stage": stage,
        "status": "cancelled",
        "next_target": "main",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DevFlow 状态与阶段门禁")
    parser.add_argument(
        "--contracts",
        type=Path,
        default=DEFAULT_CONTRACTS,
        help="阶段契约路径",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="初始化任务状态")
    init.add_argument("--workspace", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--artifact-root")
    init.add_argument("--task-id")
    init.add_argument("--size", choices=["small", "medium", "large"])
    init.add_argument("--run-mode", default="auto", choices=["auto", "manual"])
    init.add_argument("--host-adapter", default="auto")
    init.add_argument("--default-branch")
    init.add_argument("--coding-standards")

    status = subparsers.add_parser("status", help="只读查看状态")
    status.add_argument("--state", required=True)

    classify = subparsers.add_parser("classify", help="记录 Phase 0 规模判定")
    classify.add_argument("--state", required=True)
    classify.add_argument("--size", required=True, choices=["small", "medium", "large"])
    classify.add_argument("--reason", required=True)

    handoff = subparsers.add_parser("handoff", help="生成阶段任务卡")
    handoff.add_argument("--state", required=True)
    handoff.add_argument("--stage", required=True)
    handoff.add_argument("--model")
    handoff.add_argument("--reasoning-effort")
    handoff.add_argument("--output")

    spawn = subparsers.add_parser("record-spawn", help="登记 Agent 派发")
    spawn.add_argument("--state", required=True)
    spawn.add_argument("--stage", required=True)
    spawn.add_argument("--handle", required=True)
    spawn.add_argument("--host", default="codex")
    spawn.add_argument("--model")
    spawn.add_argument("--reasoning-effort")
    spawn.add_argument("--fork-turns")

    confirm = subparsers.add_parser("confirm", help="记录用户需求确认")
    confirm.add_argument("--state", required=True)
    confirm.add_argument("--stage", default="TASK-01")
    confirm.add_argument("--note", required=True)

    validate = subparsers.add_parser("validate", help="校验阶段产物")
    validate.add_argument("--state", required=True)
    validate.add_argument("--stage", required=True)

    complete = subparsers.add_parser("complete", help="校验并完成阶段")
    complete.add_argument("--state", required=True)
    complete.add_argument("--stage", required=True)

    fail = subparsers.add_parser("fail", help="记录阶段失败或阻塞")
    fail.add_argument("--state", required=True)
    fail.add_argument("--stage", required=True)
    fail.add_argument("--error-class", required=True)
    fail.add_argument("--error", required=True)
    fail.add_argument("--next-target")
    fail.add_argument("--status", default="failed", choices=["failed", "blocked"])

    abort = subparsers.add_parser("abort", help="中止工作流并保留产物")
    abort.add_argument("--state", required=True)
    abort.add_argument("--stage")
    abort.add_argument("--reason", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contracts_path = Path(args.contracts).resolve()
    try:
        contracts = load_contracts(contracts_path)
        if args.command == "init":
            result = command_init(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "status":
            print(json.dumps(command_status(args), ensure_ascii=False, indent=2))
            return 0
        if args.command == "classify":
            result = command_classify(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "handoff":
            output = command_handoff(args, contracts)
            if args.output:
                print(output)
            else:
                print(output, end="")
            return 0
        if args.command == "record-spawn":
            result = command_record_spawn(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "confirm":
            result = command_confirm(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "validate":
            result = command_validate(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if not result["errors"] else 1
        if args.command == "complete":
            result = command_complete(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("status") == "passed" else 1
        if args.command == "fail":
            result = command_fail(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "abort":
            result = command_abort(args, contracts)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except (WorkflowError, RegistryError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
