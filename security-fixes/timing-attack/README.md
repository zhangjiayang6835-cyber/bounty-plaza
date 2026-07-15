# 密码验证时序攻击修复方案

## 任务信息

- **任务编号**: #289
- **漏洞类型**: Timing Attack on Password Verification
- **赏金**: $120
- **难度**: Medium

## 修复方案

使用 Python 标准库的 secrets.compare_digest() 进行 constant-time 比较。

## 测试运行

```bash
cd security-fixes/timing-attack
pytest test_timing_attack.py -v
```
