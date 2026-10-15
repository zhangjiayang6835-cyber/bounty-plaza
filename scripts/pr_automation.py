#!/usr/bin/env python3
"""
Bounty Plaza PR Bulk Processing Automation
用途: 自动化标记、分类、消重和优先级排序
"""

import json
import os
import re
from datetime import datetime

from github import Github
from github.GithubException import GithubException

# ============================================
# 1️⃣  重复PR检测与消重
# ============================================

DUPLICATE_PATTERNS = {
    "CI Build Pipeline": {
        "keywords": ["ci build", "missing block", "cleaning _temp"],
        "issues": [1227, 1267, 1284, 1417, 1440, 1505, 1534, 1392, 1431],
        "canonical": 1227,
        "action": "close_as_duplicate"
    },
    "Custom Block Schema": {
        "keywords": ["custom block", "schema validation", "bedrock"],
        "issues": [1234, 1265, 1273, 1326, 1437, 1467, 1501, 1525],
        "canonical": 1234,
        "action": "close_as_duplicate"
    },
    "Script API Command": {
        "keywords": ["script api", "slash command", "startup"],
        "issues": [1231, 1269, 1288, 1333, 1413, 1428, 1471, 1503, 1515, 1530, 1545],
        "canonical": 1231,
        "action": "close_as_duplicate"
    },
    "Deploy ENOENT": {
        "keywords": ["deploy", "enoent", "windows", "development pack"],
        "issues": [1235, 1236, 1243, 1250, 1266, 1281, 1327, 1360, 1409, 1460, 1526],
        "canonical": 1235,
        "action": "close_as_duplicate"
    },
    "Hitbox Collision": {
        "keywords": ["hitbox", "collision", "dropout", "kinematic"],
        "issues": [1212, 1233, 1253, 1264, 1324, 1330, 1448, 1470, 1527],
        "canonical": 1212,
        "action": "close_as_duplicate"
    },
    "Dynamic Voxel": {
        "keywords": ["voxel", "display", "optimize", "draw call"],
        "issues": [1209, 1232, 1263, 1325, 1353, 1385, 1410, 1445, 1469, 1493, 1502, 1528, 1544],
        "canonical": 1209,
        "action": "close_as_duplicate"
    },
    "Humanoid NPC Texture": {
        "keywords": ["humanoid", "npc", "texture", "mirroring"],
        "issues": [1228, 1256, 1262, 1277, 1288, 1320, 1431, 1439, 1459, 1476, 1531],
        "canonical": 1228,
        "action": "close_as_duplicate"
    },
    "Template Expansion": {
        "keywords": ["template", "expansion", "deploy", "build script"],
        "issues": [1230, 1259, 1274, 1279, 1282, 1322, 1330, 1412, 1429, 1455, 1473, 1546],
        "canonical": 1230,
        "action": "close_as_duplicate"
    }
}

def detect_duplicates(pr):
    """检测重复PR"""
    title_lower = pr.title.lower()
    body_lower = pr.body.lower() if pr.body else ""
    full_text = title_lower + " " + body_lower
    
    for pattern_name, info in DUPLICATE_PATTERNS.items():
        if any(keyword in full_text for keyword in info["keywords"]):
            if pr.number != info["canonical"]:
                return {
                    "is_duplicate": True,
                    "canonical_pr": info["canonical"],
                    "pattern": pattern_name,
                    "action": info["action"]
                }
    return {"is_duplicate": False}

def auto_close_duplicates(repo, dry_run=True):
    """自动关闭重复PR"""
    processed = 0
    skipped = 0
    errors = []
    
    print("\n🔄 开始处理重复PR...")
    print(f"   模式: {'DRY-RUN (不修改)' if dry_run else '实际执行'}\n")
    
    for pattern_name, info in DUPLICATE_PATTERNS.items():
        canonical = info["canonical"]
        dup_list = info["issues"]
        
        print(f"   [{pattern_name}]")
        print(f"   正版PR: #{canonical}")
        print(f"   重复PR: {len(dup_list)} 个")
        
        for dup_pr_num in dup_list:
            if dup_pr_num == canonical:
                continue
            
            try:
                pr = repo.get_pull(dup_pr_num)
                
                if pr.state == "closed":
                    skipped += 1
                    continue
                
                if dry_run:
                    print(f"      [DRY-RUN] #{dup_pr_num} 将被关闭 -> #{canonical}")
                    processed += 1
                else:
                    # 实际操作
                    comment = (
                        f"🔄 **Duplicate of #{canonical}**\n\n"
                        f"This PR is a duplicate. "
                        f"Please see #{canonical} for the canonical solution.\n\n"
                        f"_Closed by automated PR management system._"
                    )
                    pr.create_issue_comment(comment)
                    pr.edit(state="closed")
                    print(f"      ✅ #{dup_pr_num} 已关闭")
                    processed += 1
                    
            except GithubException as e:
                errors.append(f"#{dup_pr_num}: {e!s}")
                print(f"      ❌ #{dup_pr_num} - 错误: {e!s}")
        
        print()
    
    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors
    }

# ============================================
# 2️⃣  自动标记系统
# ============================================

LABEL_COLORS = {
    "priority-critical": "d73a49",
    "priority-high": "cb2431",
    "priority-medium": "f5a623",
    "priority-low": "d4c5f9",
    "type-bugfix": "0052cc",
    "type-feature": "7057ff",
    "type-docs": "0075ca",
    "type-refactor": "2f5496",
    "domain-bedrock": "b60205",
    "domain-smart-contract": "fbca04",
    "domain-performance": "0e8a16",
    "domain-security": "e11d21",
    "bounty": "ffd700",
    "bounty-high-value": "ff6b6b",
    "bounty-medium-value": "ffa502",
    "status-needs-review": "cccccc",
    "status-duplicate": "999999",
}

def ensure_labels_exist(repo):
    """确保所有标签都存在"""
    existing_labels = {label.name for label in repo.get_labels()}
    
    for label_name, color in LABEL_COLORS.items():
        if label_name not in existing_labels:
            try:
                repo.create_label(name=label_name, color=color)
                print(f"   ✅ 创建标签: {label_name}")
            except GithubException:
                print(f"   ⚠️  标签已存在或无法创建: {label_name}")

def auto_label_pr(pr):
    """根据PR内容自动添加标签"""
    labels = []
    title = pr.title.lower()
    body = pr.body.lower() if pr.body else ""
    
    # 优先级标签
    if any(keyword in title for keyword in ["critical", "$1500", "$1400", "$7500", "$5000"]):
        labels.append("priority-critical")
    elif any(keyword in title for keyword in ["high", "$1000", "$1200"]):
        labels.append("priority-high")
    elif any(keyword in title for keyword in ["medium", "$500", "$600", "$700"]):
        labels.append("priority-medium")
    else:
        labels.append("priority-low")
    
    # 类型标签
    if "fix" in title or "🐛" in pr.title:
        labels.append("type-bugfix")
    elif "feat" in title or "✨" in pr.title:
        labels.append("type-feature")
    elif "docs" in title or "📝" in pr.title:
        labels.append("type-docs")
    elif "refactor" in title:
        labels.append("type-refactor")
    
    # 领域标签
    if any(keyword in title for keyword in ["bedrock", "minecraft", "block", "npc", "animation", "hitbox"]):
        labels.append("domain-bedrock")
    if any(keyword in title for keyword in ["erc", "anchor", "solana", "contract", "vault", "staking"]):
        labels.append("domain-smart-contract")
    if any(keyword in title for keyword in ["performance", "optimize", "voxel", "draw"]):
        labels.append("domain-performance")
    if any(keyword in title for keyword in ["security", "vulnerability", "injection", "reentrancy"]):
        labels.append("domain-security")
    
    # 赏金标签
    if "[bounty" in title or "bounty" in body:
        labels.append("bounty")
        # 提取赏金金额
        match = re.search(r'\$([0-9,]+)', title + body)
        if match:
            amount = int(match.group(1).replace(',', ''))
            if amount >= 5000:
                labels.append("bounty-high-value")
            elif amount >= 1000:
                labels.append("bounty-medium-value")
    
    # 检查重复
    if any(dup_info["canonical"] == pr.number for dup_info in DUPLICATE_PATTERNS.values()):
        labels.append("status-duplicate")
    
    return list(set(labels))  # 去重

def batch_label_prs(repo, limit=None, dry_run=True):
    """批量标记PR"""
    labeled_count = 0
    skipped_count = 0
    errors = []
    
    print("\n🏷️  开始标记PR...")
    print(f"   模式: {'DRY-RUN (不修改)' if dry_run else '实际执行'}\n")
    
    pulls = repo.get_pulls(state="open", sort="created")
    
    for i, pr in enumerate(pulls):
        if limit and labeled_count >= limit:
            break
        
        labels = auto_label_pr(pr)
        
        if dry_run:
            if i < 10:  # 只显示前10个
                print(f"   #{pr.number}: {labels}")
            labeled_count += 1
        else:
            try:
                # 移除现有标签
                for label in pr.labels:
                    pr.remove_from_labels(label.name)
                
                # 添加新标签
                for label in labels:
                    try:
                        pr.add_to_labels(label)
                    except GithubException:
                        pass
                
                labeled_count += 1
                if labeled_count % 10 == 0:
                    print(f"   已标记: {labeled_count} PR")
                    
            except GithubException as e:
                errors.append(f"#{pr.number}: {e!s}")
                skipped_count += 1
    
    if dry_run and pulls.totalCount > 10:
        print(f"   ... 以及其他 {pulls.totalCount - 10} 个PR")
    
    return {
        "labeled": labeled_count,
        "skipped": skipped_count,
        "errors": errors,
        "total": pulls.totalCount
    }

# ============================================
# 3️⃣  优先级排序与处理计划
# ============================================

def generate_priority_list(repo):
    """生成优先级处理列表"""
    priority_map = {
        "priority-critical": 1,
        "domain-security": 1,
        "bounty-high-value": 2,
        "type-feature": 3,
        "type-bugfix": 4,
        "priority-high": 2,
        "priority-medium": 5,
        "priority-low": 6
    }
    
    pr_priorities = []
    
    print("\n📋 生成优先级列表...")
    
    for pr in repo.get_pulls(state="open"):
        priority = min(
            [priority_map.get(label.name, 10) for label in pr.labels]
            or [10]
        )
        bounty_value = 0
        match = re.search(r'\$([0-9,]+)', pr.title)
        if match:
            bounty_value = int(match.group(1).replace(',', ''))
        
        pr_priorities.append({
            "number": pr.number,
            "title": pr.title[:80],
            "priority": priority,
            "bounty": bounty_value,
            "created": pr.created_at.isoformat(),
            "author": pr.user.login,
            "url": pr.html_url,
            "labels": [label.name for label in pr.labels]
        })
    
    # 排序: 优先级 -> 赏金值 -> 创建时间
    pr_priorities.sort(
        key=lambda x: (x['priority'], -x['bounty'], x['created'])
    )
    
    return pr_priorities

# ============================================
# 4️⃣  主执行函数
# ============================================

def main():
    """主处理流程"""
    
    # 获取Token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ 错误: 未找到 GITHUB_TOKEN 环境变量")
        print("   请设置: export GITHUB_TOKEN=your_token")
        return
    
    print("=" * 60)
    print("🚀 Bounty Plaza PR 自动化处理系统")
    print("=" * 60)
    
    try:
        g = Github(token)
        repo = g.get_repo("zhangjiayang6835-cyber/bounty-plaza")
        print(f"\n✅ 已连接到仓库: {repo.full_name}")
        print(f"   开放PR数: {repo.open_issues_count}")
        
    except GithubException as e:
        print(f"❌ 连接失败: {e!s}")
        return
    
    # DRY-RUN 模式
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    print(f"\n   执行模式: {'🟡 DRY-RUN (模拟)' if dry_run else '🔴 实际执行'}")
    
    # 步骤1: 确保标签存在
    print("\n1️⃣  初始化标签系统...")
    ensure_labels_exist(repo)
    
    # 步骤2: 检测并关闭重复PR
    print("\n2️⃣  检测重复PR...")
    dup_results = auto_close_duplicates(repo, dry_run=dry_run)
    print(f"   ✅ 已处理: {dup_results['processed']} 个重复PR")
    if dup_results['errors']:
        print(f"   ⚠️  错误: {len(dup_results['errors'])} 个")
    
    # 步骤3: 自动标记PR
    print("\n3️⃣  自动标记PR...")
    label_results = batch_label_prs(repo, limit=None, dry_run=dry_run)
    print(f"   ✅ 已处理: {label_results['labeled']} / {label_results['total']} PR")
    if label_results['errors']:
        print(f"   ⚠️  错误: {len(label_results['errors'])} 个")
    
    # 步骤4: 生成优先级列表
    print("\n4️⃣  生成优先级处理列表...")
    priorities = generate_priority_list(repo)
    
    print("\n📊 TOP 20 优先级PR:")
    print("-" * 120)
    print(f"{'#':<6} {'优先级':<8} {'赏金':<8} {'标签':<20} {'标题':<60}")
    print("-" * 120)
    
    for pr in priorities[:20]:
        priority_names = {1: "🔴关键", 2: "🟠高", 3: "🟡中高", 4: "🟡中", 5: "🟢中低", 6: "🟢低"}
        labels_str = ", ".join(pr['labels'][:2])
        print(f"{pr['number']:<6} {priority_names.get(pr['priority'], '?'):<8} "
              f"${pr['bounty']:<7} {labels_str:<20} {pr['title']:<60}")
    
    # 导出为JSON
    output_file = "pr_report.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "repository": repo.full_name,
        "dry_run": dry_run,
        "summary": {
            "duplicates_processed": dup_results['processed'],
            "prs_labeled": label_results['labeled'],
            "total_prs": label_results['total'],
        },
        "top_50_prs": priorities[:50]
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("✅ 处理完成!")
    print(f"   • 已关闭重复PR: {dup_results['processed']}")
    print(f"   • 已标记PR: {label_results['labeled']}")
    print(f"   • 优先级报告: {output_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
