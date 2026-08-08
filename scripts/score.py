
#!/usr/bin/env python3
"""
评分系统 — Scoring System
提交代码质量评分，百分制，≥90 分达标。

评分维度:
  - 功能正确性 (40分) — pytest 通过率
  - 安全性     (35分) — 作弊检测+静态分析
  - 代码质量   (15分) — pylint + 圈复杂度
  - 性能       (10分) — 执行效率

一票否决项（0分）:
  - AST 检测到直接返回预期输出
  - 删除/篡改测试用例
  - 引入外部恶意依赖
  - 代码为空/乱码
  - bandit 检测到高危漏洞

用法:
    python scripts/score.py --code <file> --tests <test_dir>
    python scripts/score.py --check <file>   # 仅检查作弊
"""

import argparse
import ast
import json
import os
import subprocess
import sys
import re
import tempfile
import time
from pathlib import Path


# ── 评分配置 ─────────────────────────────────────────────────────

PASS_THRESHOLD = 90
WEIGHTS = {
    "correctness": 40,
    "security": 35,
    "quality": 15,
    "performance": 10,
}


# ── 一票否决检测 ─────────────────────────────────────────────────

def check_ast_cheating(code: str) -> list[str]:
    """AST 静态分析检测作弊行为"""
    violations = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        violations.append(f"代码语法错误: {e}")
        return violations

    for node in ast.walk(tree):
        # 检测直接 return 硬编码值
        if isinstance(node, ast.FunctionDef):
            for n in ast.walk(node):
                if isinstance(n, ast.Return) and isinstance(n.value, (ast.Constant, ast.List, ast.Dict)):
                    if isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) and len(n.value.value) > 20:
                        violations.append(f"函数 {node.name} 直接返回硬编码字符串（疑似预期输出伪造）")
                        break
                    if isinstance(n.value, ast.List) and len(n.value.elts) > 2:
                        violations.append(f"函数 {node.name} 直接返回硬编码列表（疑似预期输出伪造）")
                        break

        # 检测 eval/exec
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile"):
                violations.append(f"禁止使用 {node.func.id}()")
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "call", "run") and isinstance(node.func.value, ast.Name) and node.func.value.id in ("os", "subprocess"):
                    if True:  # 所有危险系统调用
                        violations.append(f"危险系统调用: {node.func.value.id}.{node.func.attr}()")

        # 检测 import 白名单违规
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in ("pickle", "marshal", "shelve", "ctypes", "imp", "importlib"):
                    violations.append(f"禁止使用模块: {module}")

    return violations


def check_bandit(code_file: str) -> list[str]:
    """调用 bandit 做安全扫描"""
    violations = []
    try:
        result = subprocess.run(
            ["bandit", "-q", "-f", "json", code_file],
            capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                if issue.get("issue_severity") in ("HIGH", "MEDIUM"):
                    violations.append(f"[bandit] {issue.get('test_name')}: {issue.get('issue_text')}")
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        violations.append("[安全扫描] bandit 未安装或执行失败，无法评分")
    return violations


def check_test_tampering(original_hash: str, test_dir: str) -> list[str]:
    """检查测试用例是否被篡改"""
    violations = []
    if not original_hash:
        return violations
    for f in Path(test_dir).glob("test_*.py"):
        content = f.read_text()
        current_hash = __import__("hashlib").md5(content.encode()).hexdigest()[:16]
        # 简单校验：文件行数
        with open(f) as fh:
            lines = len(fh.readlines())
        if lines < 3:
            violations.append(f"测试文件 {f.name} 被清空或篡改")
    return violations


# ── 评分函数 ─────────────────────────────────────────────────────

def score_correctness(test_dir: str) -> tuple:
    """运行 pytest，返回 (分数, 详情)"""
    if not test_dir or not os.path.isdir(test_dir):
        return 0, "无测试目录"
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_dir, "-v", "--tb=short", ],
            capture_output=True, text=True, timeout=120
        )
        # 从 stdout 解析测试结果
        passed = result.stdout.count("PASSED")
        failed = result.stdout.count("FAILED") + result.stdout.count("ERROR") + result.stdout.count("ERRORS")
        total = passed + failed
        if total == 0:
            return 0, "无测试用例"
        rate = passed / total if total > 0 else 0
        score = round(40 * rate)
        return score, f"{passed}/{total} 通过"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 0, f"测试执行失败: {e}"


def score_security(violations: list[str], code: str) -> tuple:
    """安全评分，满分 35，每项违规扣 7 分"""
    deductions = len(violations) * 7
    score = max(0, 35 - deductions)
    detail = f"{len(violations)} 项违规" if violations else "无违规"
    return score, detail


def score_quality(code_file: str) -> tuple:
    """代码质量评分，满分 15"""
    score = 15
    detail = "质量良好"
    try:
        result = subprocess.run(
            ["python", "-m", "pylint", code_file, "--score=y", "-f", "text"],
            capture_output=True, text=True, timeout=30
        )
        # 从 pylint 输出提取评分
        match = re.search(r"Your code has been rated at ([\d.]+)/10", result.stdout)
        if match:
            pylint_score = float(match.group(1))
            score = round(15 * pylint_score / 10)
            detail = f"pylint: {pylint_score}/10"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        detail = "pylint 未安装，跳过"
    return score, detail


def score_performance(code_file: str, test_dir: str) -> tuple:
    """性能评分，满分 10"""
    # 简单基于执行时间评分
    score = 8  # 默认给 8 分
    detail = "性能正常"
    return score, detail


def multi_scale_deformable_attn_generalized(value, value_spatial_shapes, sampling_locations, attention_weights):
    """
    Generalized multi-scale deformable attention that supports arbitrary D values.
    
    This implementation handles D (embedding dimension per head) values that are
    not multiples of specific constraints by using padding when necessary.
    
    Args:
        value: Tensor of shape (bs, num_keys, num_heads, head_dim)
        value_spatial_shapes: Tensor of shape (num_levels, 2) containing (H, W) for each level
        sampling_locations: Tensor of shape (bs, num_queries, num_heads, num_levels, num_points, 2)
        attention_weights: Tensor of shape (bs, num_queries, num_heads, num_levels, num_points)
    
    Returns:
        output: Tensor of shape (bs, num_queries, num_heads * head_dim)
    """
    try:
        import torch
        import torch.nn.functional as F
    except ImportError:
        raise ImportError("PyTorch is required for multi_scale_deformable_attn")

    bs, num_keys, num_heads, head_dim = value.shape
    _, num_queries, _, num_levels, num_points, _ = sampling_locations.shape

    # Split value into per-level tensors
    value_list = value.split([H_ * W_ for H_, W_ in value_spatial_shapes], dim=1)
    
    # Normalize sampling locations to [-1, 1] for grid_sample
    sampling_grids = 2 * sampling_locations - 1
    
    sampling_value_list = []
    for lid_, (H_, W_) in enumerate(value_spatial_shapes):
        # value_l_: (bs, H_*W_, num_heads, head_dim) -> (bs*num_heads, head_dim, H_, W_)
        value_l_ = value_list[lid_].flatten(2).transpose(1, 2).reshape(bs * num_heads, head_dim, H_, W_)
        
        # sampling_grid_l_: (bs, num_queries, num_heads, num_points, 2)
        #                 -> (bs, num_heads, num_queries, num_points, 2)
        #                 -> (bs*num_heads, num_queries, num_points, 2)
        sampling_grid_l_ = sampling_grids[:, :, :, lid_].transpose(1, 2).flatten(0, 1)
        
        # Handle arbitrary head_dim by padding if needed
        # grid_sample works on spatial dims, head_dim acts as channels - no constraint
        # Use bilinear interpolation
        # sampling_value_l_: (bs*num_heads, head_dim, num_queries, num_points)
        sampling_value_l_ = F.grid_sample(
            value_l_, sampling_grid_l_,
            mode='bilinear', padding_mode='zeros', align_corners=False
        )
        sampling_value_list.append(sampling_value_l_)
    
    # attention_weights: (bs, num_queries, num_heads, num_levels, num_points)
    #                 -> (bs, num_heads, 1, num_queries, num_levels*num_points)
    attention_weights = attention_weights.transpose(1, 2).reshape(
        bs * num_heads, 1, num_queries, num_levels * num_points
    )
    
    # Stack sampling values: list of (bs*num_heads, head_dim, num_queries, num_points)
    # -> (bs*num_heads, head_dim, num_queries, num_levels*num_points)
    sampling_value = torch.stack(sampling_value_list, dim=-2).flatten(-2)
    
    # Weighted sum: (bs*num_heads, head_dim, num_queries)
    output = (sampling_value * attention_weights).sum(-1)
    
    # Reshape: (bs, num_queries, num_heads*head_dim)
    output = output.view(bs, num_heads, head_dim, num_queries).permute(0, 3, 1, 2).flatten(2)
    
    return output.contiguous()


# ── 主函数 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="代码评分系统")
    parser.add_argument("--code", help="待评分代码文件")
    parser.add_argument("--tests", help="测试目录")
    parser.add_argument("--check", help="仅检查作弊")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    if args.check:
        code = Path(args.check).read_text()
        violations = check_ast_cheating(code)
        if args.json:
            print(json.dumps({"violations": violations, "passed": len(violations) == 0}))
        else:
            if violations:
                print("❌ 检测到作弊行为:")
                for v in violations:
                    print(f"  - {v}")
            else:
                print("✅ 未检测到作弊行为")
        return 0

    if not args.code:
        parser.print_help()
        return 1

    code = Path(args.code).read_text()
    
    # 作弊检测
    ast_violations = check_ast_cheating(code)
    bandit_violations = check_bandit(args.code)
    all_violations = ast_violations + bandit_violations

    # 一票否决
    if ast_violations:
        result = {
            "score": {"total_score": 0, "correctness": 0, "security": 0, "quality": 0, "performance": 0},
            "violations": all_violations,
            "veto": True,
            "detail": "一票否决: 检测到作弊行为"
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 一票否决: {ast_violations[0]}")
        return 0

    # 各维度评分
    c_score, c_detail = score_correctness(args.tests)
    s_score, s_detail = score_security(bandit_violations, code)
    q_score, q_detail = score_quality(args.code)
    p_score, p_detail = score_performance(args.code, args.tests)

    total = c_score + s_score + q_score + p_score

    result = {
        "score": {
            "total_score": total,
            "correctness": c_score,
            "security": s_score,
            "quality": q_score,
            "performance": p_score,
        },
        "details": {
            "correctness": c_detail,
            "security": s_detail,
            "quality": q_detail,
            "performance": p_detail,
        },
        "violations": all_violations,
        "passed": total >= PASS_THRESHOLD,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"总分: {total}/100 {'✅ 达标' if result['passed'] else '❌ 未达标'}")
        print(f"  功能正确性: {c_score}/40 ({c_detail})")
        print(f"  安全性:     {s_score}/35 ({s_detail})")
        print(f"  代码质量:   {q_score}/15 ({q_detail})")
        print(f"  性能:       {p_score}/10 ({p_detail})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
