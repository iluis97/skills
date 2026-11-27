from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import role_registry
import workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name).resolve()
        self.contracts = workflow.load_contracts(workflow.DEFAULT_CONTRACTS)
        init_args = Namespace(
            workspace=str(self.workspace),
            slug="demo",
            artifact_root=str(self.workspace / "artifacts"),
            task_id=None,
            size="medium",
            run_mode="auto",
            host_adapter="auto",
            default_branch=None,
            coding_standards="stdlib",
        )
        workflow.command_init(init_args, self.contracts)
        self.state_path = self.workspace / "artifacts" / "demo" / "workflow-state.json"
        self.artifacts_dir = self.state_path.parent

    def tearDown(self):
        self.temp.cleanup()

    def write_doc(self, relative_path, stage, title, sections, extra=""):
        path = self.artifacts_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "---",
            "task_id: demo",
            f"stage: {stage}",
            "author: test",
            "date: 2026-11-18",
            "run_mode: auto",
            "---",
            "",
            f"# {title}",
            "",
        ]
        for section in sections:
            lines.extend(
                [
                    f"## {section}",
                    (
                        f"这是 {section} 的可验证内容，用于覆盖阶段门禁和文档结构检查。"
                        "该段补充足够的实际说明，确保测试关注结构与契约，而不是文档长度本身。"
                        "同时保留真实可核对的信息，避免用空泛内容掩盖门禁问题。"
                    ),
                    "",
                ]
            )
        if extra:
            lines.extend([extra, ""])
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def write_result(self, relative_path, stage, role_id, artifacts, **overrides):
        path = self.artifacts_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        result = {
            "stage": stage,
            "role_id": role_id,
            "status": "passed",
            "artifacts": artifacts,
            "checks": [
                {
                    "name": "contract check",
                    "result": "passed",
                    "evidence": "test",
                }
            ],
            "risks": [],
            "last_error": None,
            "error_class": None,
        }
        result.update(overrides)
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def complete(self, stage):
        return workflow.command_complete(
            Namespace(state=str(self.state_path), stage=stage),
            self.contracts,
        )

    def validate(self, stage):
        return workflow.command_validate(
            Namespace(state=str(self.state_path), stage=stage),
            self.contracts,
        )

    def prepare_requirement(self):
        return self.write_doc(
            "01-requirement/requirement-report.md",
            "TASK-01",
            "需求报告",
            [
                "原始需求",
                "代码与上下文分析",
                "澄清 Q&A",
                "收敛结论",
                "纳入范围",
                "排除范围",
                "成功标准",
                "影响面与风险",
                "待确认问题",
            ],
        )

    def confirm_requirement(self):
        return workflow.command_confirm(
            Namespace(
                state=str(self.state_path),
                stage="TASK-01",
                note="user confirmed requirements",
            ),
            self.contracts,
        )

    def prepare_design(self):
        self.write_doc(
            "02-design/tech-design.md",
            "TASK-02",
            "技术方案",
            [
                "背景与已确认需求",
                "现状与调用链",
                "方案概述",
                "具体变更点",
                "接口与数据模型",
                "兼容性",
                "风险与回滚",
                "验证命令与测试策略",
                "明确不做",
            ],
        )
        app_js = self.workspace / "app.js"
        plan = f"""---
task_id: demo
stage: TASK-02
author: test
date: 2026-11-18
run_mode: auto
---

# 执行计划

```yaml
task_slug: demo
parallel_tasks:
  - id: PT-01
    title: 实现页面
    files_whitelist:
      - {app_js}
    pseudocode: |
      create scene
      bind pointer
      interpolate colors
      render sun
      run syntax check
    acceptance:
      - app.js exists
```
"""
        plan_path = self.artifacts_dir / "02-design" / "execution-plan.md"
        plan_path.write_text(plan, encoding="utf-8")
        result = self.write_result(
            "02-design/stage-result.json",
            "TASK-02",
            "architect",
            [
                "02-design/tech-design.md",
                "02-design/execution-plan.md",
            ],
        )
        return app_js, plan_path, result

    def prepare_code(self, app_js):
        app_js.write_text("const ready = true;\n", encoding="utf-8")
        extra = "| PT | Acceptance | Result | Evidence |\n|---|---|---|---|\n| PT-01 | app.js exists | PASS | app.js |"
        self.write_doc(
            "03-code/change-report.md",
            "TASK-03",
            "变更报告",
            [
                "任务和阶段",
                "实现的 PT",
                "实际变更文件",
                "方案映射",
                "Acceptance",
                "自检",
                "API 文档",
                "未运行",
                "风险",
            ],
            extra=extra,
        )
        self.write_result(
            "03-code/stage-result.json",
            "TASK-03",
            "developer",
            ["03-code/change-report.md"],
            files_changed=[str(app_js)],
            api_docs_required=False,
        )

    def test_requirement_gate_and_design_gate(self):
        self.prepare_requirement()
        blocked = self.complete("TASK-01")
        self.assertIn("尚未记录用户需求确认", "\n".join(blocked["errors"]))
        self.confirm_requirement()
        completed = self.complete("TASK-01")
        self.assertEqual(completed["next_target"], "architect")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["stages"]["TASK-01"]["status"], "completed")

        incomplete = self.validate("TASK-02")
        self.assertIn(
            "缺少必需产物",
            "\n".join(incomplete["errors"]),
        )

        self.prepare_design()
        completed = self.complete("TASK-02")
        self.assertEqual(completed["next_target"], "developer")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["last_event"], "TASK-02_completed")

    def test_handoff_blocks_before_upstream_stage_completes(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        text = workflow.command_handoff(
            Namespace(
                state=str(self.state_path),
                stage="TASK-02",
                model=None,
                reasoning_effort=None,
                output=None,
            ),
            self.contracts,
        )
        self.assertIn("TASK-02 阶段任务卡", text)
        self.assertIn("stage-result.json", text)
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_handoff(
                Namespace(
                    state=str(self.state_path),
                    stage="TASK-03",
                    model=None,
                    reasoning_effort=None,
                    output=None,
                ),
                self.contracts,
            )

    def test_wrong_change_report_path_is_rejected(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        app_js, _plan_path, _result = self.prepare_design()
        self.complete("TASK-02")
        app_js.write_text("const ready = true;\n", encoding="utf-8")
        wrong = self.artifacts_dir / "03-developer" / "developer-report.md"
        wrong.parent.mkdir(parents=True)
        wrong.write_text("# wrong path\n", encoding="utf-8")
        self.write_result(
            "03-code/stage-result.json",
            "TASK-03",
            "developer",
            ["03-code/change-report.md"],
            files_changed=[str(app_js)],
        )
        report = self.validate("TASK-03")
        joined = "\n".join(report["errors"])
        self.assertIn(str(self.artifacts_dir / "03-code" / "change-report.md"), joined)
        self.assertIn("缺少必需产物", joined)

    def test_plan_scope_violation_is_rejected(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        app_js, _plan_path, _result = self.prepare_design()
        self.complete("TASK-02")
        self.prepare_code(app_js)
        result_path = self.artifacts_dir / "03-code" / "stage-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["files_changed"] = [str(self.workspace / "outside.js")]
        result_path.write_text(json.dumps(result), encoding="utf-8")
        report = self.validate("TASK-03")
        self.assertIn(
            "越出执行计划白名单",
            "\n".join(report["errors"]),
        )

    def test_full_workflow_reaches_summary(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        app_js, _plan_path, _result = self.prepare_design()
        self.complete("TASK-02")
        self.prepare_code(app_js)
        self.assertEqual(self.complete("TASK-03")["next_target"], "code-reviewer")

        self.write_doc(
            "03-code/review-report.md",
            "CODE-REVIEW",
            "审查报告",
            [
                "审查结论 PASSED",
                "审查文件",
                "P0 问题",
                "P1 问题",
                "P2 建议",
                "前置门禁",
                "验收条件",
            ],
        )
        review_path = self.artifacts_dir / "03-code" / "review-report.md"
        text = review_path.read_text(encoding="utf-8")
        text = re.sub(
            r"(## P0 问题\n).*?(?=\n## )",
            r"\1无\n",
            text,
            flags=re.S,
        )
        text = re.sub(
            r"(## P1 问题\n).*?(?=\n## )",
            r"\1无\n",
            text,
            flags=re.S,
        )
        review_path.write_text(text, encoding="utf-8")
        self.write_result(
            "03-code/code-review-result.json",
            "CODE-REVIEW",
            "code-reviewer",
            ["03-code/review-report.md"],
            review_result="passed",
        )
        self.assertEqual(
            self.complete("CODE-REVIEW")["next_target"],
            "test-engineer",
        )

        self.write_doc(
            "04-e2e/test-report.md",
            "TASK-04",
            "测试报告",
            [
                "测试范围",
                "实际执行命令",
                "真实结果",
                "未运行项",
                "阻塞项",
                "剩余风险",
            ],
            extra="```bash\nnode --check app.js\n```",
        )
        self.write_doc(
            "04-e2e/added-cases.md",
            "TASK-04",
            "测试用例",
            [
                "新增或修改的测试文件",
                "场景覆盖",
                "运行前提",
                "变更行为",
            ],
        )
        self.write_result(
            "04-e2e/stage-result.json",
            "TASK-04",
            "test-engineer",
            ["04-e2e/test-report.md", "04-e2e/added-cases.md"],
        )
        self.assertEqual(
            self.complete("TASK-04")["next_target"],
            "knowledge-engineer",
        )

        self.write_doc(
            "05-knowledge/knowledge-report.md",
            "TASK-05",
            "知识报告",
            ["新增条目", "合并", "未沉淀", "冲突"],
        )
        self.write_result(
            "05-knowledge/stage-result.json",
            "TASK-05",
            "knowledge-engineer",
            ["05-knowledge/knowledge-report.md"],
        )
        self.assertEqual(
            self.complete("TASK-05")["next_target"],
            "leader",
        )

        self.write_doc(
            "workflow-summary.md",
            "SUMMARY",
            "最终总结",
            [
                "任务",
                "阶段产物",
                "代码变更",
                "代码审查",
                "测试",
                "知识沉淀",
                "风险",
            ],
        )
        self.write_result(
            "stage-result.json",
            "SUMMARY",
            "leader",
            ["workflow-summary.md"],
        )
        completed = self.complete("SUMMARY")
        self.assertEqual(completed["event"], "workflow_completed")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["summary"]["status"], "completed")
        self.assertEqual(state["stages"]["SUMMARY"]["status"], "completed")

    def test_failed_code_review_routes_back_to_developer(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        app_js, _plan_path, _result = self.prepare_design()
        self.complete("TASK-02")
        self.prepare_code(app_js)
        self.complete("TASK-03")
        self.write_doc(
            "03-code/review-report.md",
            "CODE-REVIEW",
            "审查报告",
            [
                "审查结论 FAILED",
                "审查文件",
                "P0 问题",
                "P1 问题",
                "P2 建议",
                "前置门禁",
                "验收条件",
            ],
        )
        review_path = self.artifacts_dir / "03-code" / "review-report.md"
        text = re.sub(
            r"## P1 问题\n.*?(?=\n## )",
            "## P1 问题\n无\n",
            review_path.read_text(encoding="utf-8"),
            flags=re.S,
        )
        review_path.write_text(text, encoding="utf-8")
        self.write_result(
            "03-code/code-review-result.json",
            "CODE-REVIEW",
            "code-reviewer",
            ["03-code/review-report.md"],
            status="failed",
            review_result="failed",
            error_class="review_rejected",
            last_error="P0: production blocker",
        )
        result = self.complete("CODE-REVIEW")
        self.assertEqual(result["next_target"], "developer")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["stages"]["CODE-REVIEW"]["review_result"], "failed")

    def test_small_solo_flow_completes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            workflow.command_init(
                Namespace(
                    workspace=str(workspace),
                    slug="solo-demo",
                    artifact_root=str(workspace / "artifacts"),
                    task_id=None,
                    size="small",
                    run_mode="auto",
                    host_adapter="auto",
                    default_branch=None,
                    coding_standards="stdlib",
                ),
                self.contracts,
            )
            state_path = (
                workspace / "artifacts" / "solo-demo" / "workflow-state.json"
            )
            artifacts_dir = state_path.parent
            solo_sections = [
                "需求理解",
                "简化设计",
                "编码摘要",
                "实际改动文件",
                "验证命令",
                "未运行项",
            ]
            summary_sections = [
                "任务",
                "阶段产物",
                "代码变更",
                "代码审查",
                "测试",
                "知识沉淀",
                "风险",
            ]
            for relative_path, stage, title, sections in [
                ("01-solo/solo-report.md", "SOLO", "SOLO 报告", solo_sections),
                ("workflow-summary.md", "SUMMARY", "最终总结", summary_sections),
            ]:
                path = artifacts_dir / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                body = [
                    "---",
                    "task_id: solo-demo",
                    f"stage: {stage}",
                    "author: test",
                    "date: 2026-11-18",
                    "run_mode: auto",
                    "---",
                    "",
                ]
                for section in sections:
                    body.extend(
                        [
                            f"## {section}",
                            (
                                f"这是 {section} 的实际内容。"
                                "该段确保 SOLO 产物满足结构、长度和可验证性要求。"
                                "所有检查均来自真实执行结果。"
                            ),
                            "",
                        ]
                    )
                path.write_text("\n".join(body), encoding="utf-8")
            stage_result = artifacts_dir / "01-solo" / "stage-result.json"
            stage_result.write_text(
                json.dumps(
                    {
                        "stage": "SOLO",
                        "role_id": "solo-developer",
                        "status": "passed",
                        "artifacts": [
                            "01-solo/solo-report.md",
                            "workflow-summary.md",
                        ],
                        "checks": [
                            {
                                "name": "syntax",
                                "result": "passed",
                                "evidence": "exit 0",
                            }
                        ],
                        "risks": [],
                        "last_error": None,
                        "error_class": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            completed = workflow.command_complete(
                Namespace(state=str(state_path), stage="SOLO"),
                self.contracts,
            )
            self.assertEqual(completed["event"], "workflow_completed", completed)
            state = workflow.load_state(state_path)
            self.assertEqual(state["summary"]["status"], "completed")

    def test_model_capability_fallback(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        self.prepare_design()
        self.complete("TASK-02")
        args = Namespace(
            state=str(self.state_path),
            stage="TASK-03",
            handle="agent-1",
            host="codex",
            model="volcengine/glm-5.3-flash",
            reasoning_effort=None,
            fork_turns="none",
        )
        result = workflow.command_record_spawn(args, self.contracts)
        self.assertTrue(result["fallback"])
        self.assertEqual(result["reasoning_effort"], "high")
        self.assertIsNone(result["execution"]["submitted"])
        self.assertIn("未知（仅有配置）", result["notice"])
        args.reasoning_effort = "medium"
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(args, self.contracts)

    def prepare_dispatch(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        return self.create_dispatch()

    def create_dispatch(self):
        args = workflow.build_parser().parse_args([
            "handoff", "--state", str(self.state_path), "--stage", "TASK-02",
        ])
        workflow.command_handoff(args, self.contracts)
        plan = workflow.load_state(self.state_path)["stages"]["TASK-02"]["dispatch_plan"]
        request = self.artifacts_dir / f"request-{plan['dispatch_id']}.json"
        workflow.write_json(request, {
            "reasoning_effort": "high", "context_mode": "isolated",
            "agent_type": "worker", "host_metadata": {"fork_turns": "none"},
        })
        return workflow.build_parser().parse_args([
            "record-spawn", "--state", str(self.state_path), "--stage", "TASK-02",
            "--handle", f"agent-{plan['dispatch_id']}",
            "--dispatch-id", plan["dispatch_id"], "--request-file", str(request),
        ])

    def test_dispatch_snapshot_is_used_instead_of_reloading_roles(self):
        args = self.prepare_dispatch()
        with patch.object(workflow, "role_settings_for_stage", side_effect=AssertionError("配置不应重读")):
            result = workflow.command_record_spawn(args, self.contracts)
        execution = result["execution"]
        self.assertEqual(execution["configured"]["model"], "inherit")
        self.assertNotIn("model", execution["submitted"])
        self.assertIsNone(execution["reported"]["model"])
        self.assertEqual(execution["agent_type"], "worker")
        self.assertIn("high（已提交）", result["notice"])
        self.assertNotIn("\n", result["notice"])
        before = self.state_path.read_bytes()
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(args, self.contracts)
        self.assertEqual(before, self.state_path.read_bytes())

    def test_stale_or_changed_dispatch_requires_matching_snapshot_and_reason(self):
        args = self.prepare_dispatch()
        latest = self.create_dispatch()
        before = self.state_path.read_bytes()
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(args, self.contracts)
        workflow.write_json(Path(latest.request_file), {"context_mode": "isolated"})
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(latest, self.contracts)
        self.assertEqual(before, self.state_path.read_bytes())
        latest.fallback_reason = "宿主不接受推理等级覆盖"
        result = workflow.command_record_spawn(latest, self.contracts)
        self.assertTrue(result["fallback"])
        self.assertNotIn("已提交", result["notice"])
        self.assertEqual(result["execution"]["configured"]["reasoning_effort"], "high")

    def test_partial_host_reports_preserve_evidence_and_attempt_history(self):
        args = self.prepare_dispatch()
        args.reported_model = "provider/example-model"
        args.report_source = "spawn 响应 model 字段"
        workflow.command_record_spawn(args, self.contracts)
        report_args = workflow.build_parser().parse_args([
            "record-runtime", "--state", str(self.state_path), "--stage", "TASK-02",
            "--handle", args.handle, "--reported-reasoning-effort", "high",
            "--report-source", "宿主查询响应 reasoning_effort 字段",
        ])
        result = workflow.command_record_runtime(report_args)
        reported = result["execution"]["reported"]
        self.assertEqual(reported["model"]["source"], args.report_source)
        self.assertIn("high（已确认）", result["notice"])
        state = workflow.load_state(self.state_path)
        original = next(d for d in state["decisions"] if d["kind"] == "agent_spawned")
        self.assertIsNone(original["execution"]["reported"]["reasoning_effort"])
        report_args.handle = "wrong-agent"
        before = self.state_path.read_bytes()
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_runtime(report_args)
        self.assertEqual(before, self.state_path.read_bytes())
        retry = self.create_dispatch()
        result = workflow.command_record_spawn(retry, self.contracts)
        self.assertEqual(result["execution"]["reported"], {
            "model": None, "reasoning_effort": None,
        })
        report_args.handle = args.handle
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_runtime(report_args)

    def test_host_report_requires_source_and_concrete_value(self):
        args = self.prepare_dispatch()
        args.reported_model = "provider/example-model"
        before = self.state_path.read_bytes()
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(args, self.contracts)
        args.report_source = "spawn 响应"
        args.reported_model = "inherit"
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(args, self.contracts)
        self.assertEqual(before, self.state_path.read_bytes())

    def test_failed_spawn_and_retry_keep_separate_evidence(self):
        first = self.prepare_dispatch()
        fail_args = workflow.build_parser().parse_args([
            "fail", "--state", str(self.state_path), "--stage", "TASK-02",
            "--error-class", "provider_error", "--error", "连接失败",
            "--dispatch-id", first.dispatch_id, "--request-file", first.request_file,
        ])
        workflow.command_fail(fail_args, self.contracts)
        before_retry = self.state_path.read_bytes()
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(first, self.contracts)
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_fail(fail_args, self.contracts)
        self.assertEqual(before_retry, self.state_path.read_bytes())
        second = self.create_dispatch()
        result = workflow.command_record_spawn(second, self.contracts)
        self.assertIsNone(result["execution"]["reported"]["model"])
        status_args = workflow.build_parser().parse_args([
            "status", "--state", str(self.state_path), "--details",
        ])
        before = self.state_path.read_bytes()
        details = workflow.command_status(status_args)
        failed = next(d for d in details["decisions"] if d["kind"] == "stage_failed")
        self.assertEqual(failed["dispatch_plan"]["dispatch_id"], first.dispatch_id)
        self.assertEqual(failed["submitted"]["reasoning_effort"], "high")
        self.assertIsNone(failed["execution"])
        self.assertEqual(details["stages"]["TASK-02"]["agent_handle"], second.handle)
        self.assertEqual(before, self.state_path.read_bytes())

    def test_solo_reports_main_thread_without_claiming_role_effort_applied(self):
        workflow.command_classify(Namespace(
            state=str(self.state_path), size="small", reason="单文件修改",
        ), self.contracts)
        args = workflow.build_parser().parse_args([
            "record-execution", "--state", str(self.state_path), "--stage", "SOLO",
            "--mode", "main_thread",
        ])
        result = workflow.command_record_execution(args, self.contracts)
        self.assertEqual(result["execution"]["configured"]["reasoning_effort"], "medium")
        self.assertEqual(result["execution"]["submitted"], {})
        self.assertIsNone(result["execution"]["agent_handle"])
        self.assertIn("主线程", result["notice"])
        self.assertNotIn("medium", result["notice"])
        spawn = workflow.build_parser().parse_args([
            "record-spawn", "--state", str(self.state_path), "--stage", "SOLO", "--handle", "fake",
        ])
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_spawn(spawn, self.contracts)

    def test_inline_execution_records_unavailable_reason(self):
        self.prepare_dispatch()
        args = workflow.build_parser().parse_args([
            "record-execution", "--state", str(self.state_path), "--stage", "TASK-02",
            "--mode", "inline",
        ])
        with self.assertRaises(workflow.WorkflowError):
            workflow.command_record_execution(args, self.contracts)
        args.reason = "当前宿主没有子 Agent 工具"
        result = workflow.command_record_execution(args, self.contracts)
        self.assertIn("内联降级", result["notice"])
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["decisions"][-1]["kind"], "agent_spawn_unavailable")

    def test_invalid_submitted_parameters_do_not_write_state(self):
        args = self.prepare_dispatch()
        before = self.state_path.read_bytes()
        for submitted in (
            {"model": "inherit", "context_mode": "isolated"},
            {"reasoning_effort": "high"},
            {"reasoning_effort": "high", "context_mode": "isolated", "message": "提示词"},
            {"reasoning_effort": "high", "context_mode": "inherit"},
        ):
            with self.subTest(submitted=submitted):
                workflow.write_json(Path(args.request_file), submitted)
                args.fallback_reason = "测试宿主参数边界"
                with self.assertRaises(workflow.WorkflowError):
                    workflow.command_record_spawn(args, self.contracts)
                self.assertEqual(before, self.state_path.read_bytes())

    def test_legacy_status_remains_read_only_without_fabricating_execution(self):
        state = workflow.load_state(self.state_path)
        state["stages"]["TASK-02"].update({
            "agent_handle": "old-agent", "model": "inherit", "reasoning_effort": "high",
        })
        workflow.write_json(self.state_path, state)
        before = self.state_path.read_bytes()
        result = workflow.command_status(Namespace(state=str(self.state_path)))
        stage = result["stages"]["TASK-02"]
        self.assertTrue(stage["configuration_only"])
        self.assertIsNone(stage["execution"])
        self.assertNotIn("decisions", result)
        self.assertEqual(before, self.state_path.read_bytes())

    def test_state_event_mismatch_is_rejected(self):
        state = workflow.load_state(self.state_path)
        state["current_stage"] = "TASK-02"
        state["last_event"] = "TASK-01_completed"
        workflow.write_json(self.state_path, state)
        errors = workflow.validate_state_shape(state)
        self.assertIn("与 current_stage", "\n".join(errors))

    def test_old_state_version_is_rejected(self):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["version"] = "1.5"
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.state_path)

    def test_phase0_can_classify_after_init(self):
        result = workflow.command_classify(
            Namespace(
                state=str(self.state_path),
                size="small",
                reason="single file change",
            ),
            self.contracts,
        )
        self.assertEqual(result["next_target"], "solo-developer")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["size_class"], "small")
        self.assertEqual(state["stages"]["TASK-01"]["status"], "skipped")
        self.assertEqual(state["stages"]["SOLO"]["status"], "pending")

    def test_fail_command_records_error_class_and_route(self):
        result = workflow.command_fail(
            Namespace(
                state=str(self.state_path),
                stage="TASK-02",
                error_class="artifact_invalid",
                error="missing tech-design.md",
                next_target=None,
                status="failed",
            ),
            self.contracts,
        )
        self.assertEqual(result["next_target"], "architect")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["last_error_class"], "artifact_invalid")
        self.assertEqual(state["stages"]["TASK-02"]["status"], "failed")
        second = workflow.command_fail(
            Namespace(
                state=str(self.state_path),
                stage="TASK-02",
                error_class="artifact_invalid",
                error="still missing tech-design.md",
                next_target=None,
                status="failed",
            ),
            self.contracts,
        )
        self.assertEqual(second["next_target"], "main")
        self.assertEqual(second["status"], "blocked")

    def test_abort_preserves_state_and_marks_cancelled(self):
        self.prepare_requirement()
        self.confirm_requirement()
        self.complete("TASK-01")
        result = workflow.command_abort(
            Namespace(
                state=str(self.state_path),
                stage="TASK-01",
                reason="user requested stop",
            ),
            self.contracts,
        )
        self.assertEqual(result["event"], "workflow_aborted")
        state = workflow.load_state(self.state_path)
        self.assertEqual(state["summary"]["status"], "aborted")
        self.assertEqual(state["stages"]["TASK-01"]["status"], "cancelled")

class RoleRegistryTests(unittest.TestCase):
    def test_model_profile_reports_unsupported_effort(self):
        registry, _defaults, profiles = role_registry.load_registry(
            workflow.SKILL_ROOT,
            workflow.DEFAULT_ROLES,
        )
        compatibility = role_registry.model_compatibility(
            "volcengine/glm-5.3-flash",
            "medium",
            profiles,
        )
        self.assertFalse(compatibility["compatible"])
        self.assertEqual(
            compatibility["suggested_reasoning_effort"],
            "high",
        )
        self.assertIn("developer", registry)

    def test_contracts_roles_and_template_are_consistent(self):
        contracts = workflow.load_contracts(workflow.DEFAULT_CONTRACTS)
        registry, _defaults, _profiles = role_registry.load_registry(
            workflow.SKILL_ROOT,
            workflow.DEFAULT_ROLES,
        )
        template = json.loads(
            (workflow.SKILL_ROOT / "assets" / "workflow-state-template.json").read_text(
                encoding="utf-8"
            )
        )
        for stage, contract in contracts["stages"].items():
            self.assertIn(stage, template["stages"])
            role_id = contract["role_id"]
            if role_id == "main":
                self.assertEqual(stage, "TASK-01")
                continue
            self.assertIn(role_id, registry)
            self.assertEqual(registry[role_id]["stage"], stage)


if __name__ == "__main__":
    unittest.main()
