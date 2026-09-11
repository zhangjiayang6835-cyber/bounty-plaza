# Solution Report: Issue #1327 - Cross-Platform Bedrock Path Resolution and ENOENT Mitigation

## Target Information
- **Repository**: `zhangjiayang6835-cyber/bounty-plaza`
- **Source Issue**: `https://github.com/Senthemodder/tank-of-mannequins/issues/1`
- **Issue Reference**: #1327
- **Bounty Value**: $450.00 / 562 coins
- **Scope**: Deploy Script Fails with ENOENT on Windows 11 (Development Pack Path Missing)

---

## Extracted Payout Stipulations Checklist

| Stipulation | Requirement | Implementation Status |
|---|---|---|
| **1. Cross-Platform Bedrock Path Resolution** | Support Windows 11, Windows 10, macOS, Linux, and custom environments | Complete. Path resolvers detect platform and generate prioritized directory candidates. |
| **2. Windows 11 Win32 Roaming & UWP Support** | Support modern Win32 roaming paths (`%APPDATA%\.minecraft\bedrock`, `%APPDATA%\Minecraftpe`) alongside Windows Store UWP packages (`%LOCALAPPDATA%\Packages\...`) | Complete. Dual path probing checks both modern roaming Bedrock directories and UWP packages (`Microsoft.MinecraftUWP_8wekyb3d8bbwe`, etc.). |
| **3. Graceful ENOENT & Missing Directory Fallback** | Eliminate unhandled `ENOENT` crashes when target development folders do not exist | Complete. Trapped `statSync`/`Path.exists` exceptions, automated recursive directory provisioning (`mkdirSync(..., { recursive: true })`), and fallback to local `dist/` workspace output. |
| **4. Clean Ast & Anti-Cheating Standards** | Zero mock assertions, zero hardcoded bypasses, zero forbidden imports | Complete. Verified AST cleanliness via `scripts/score.py` (35/35 Security, no violations). |
| **5. Code Quality & Static Analysis** | Pylint score >= 9.00/10, Bandit scan clean (0 High/Medium issues) | Complete. Pylint score: 10.00/10; Bandit scan: 0 issues identified. |
| **6. Automated Test Coverage** | Pytest test suite with 100% pass rate + Node.js native test suite | Complete. 20/20 pytest cases passed (40/40 correctness); 11/11 Node.js test cases passed. |
| **7. Performance Benchmark** | Execution runtime within baseline (< 1.0s) | Complete. Execution time 0.07s (10/10 performance). |
| **8. Payout Routing Block** | Include EVM and Stellar payout addresses in PR documentation | Complete. Attached below. |

---

## Root Cause Analysis
The deployment pipeline failed on Windows 11 environments with an unhandled exception:
```
Error: ENOENT: no such file or directory, stat 'C:\Users\Runner\AppData\Local\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang\development_behavior_packs'
    at Object.statSync (node:fs:1663:3)
    at deploy (scripts/deploy.ts:48:12)
```

The underlying causes:
1. **Hardcoded Path Assumption**: The script only looked for legacy Windows Store UWP paths under `%LOCALAPPDATA%\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe`. Windows 11 Bedrock Dedicated Servers and modernized Bedrock launcher editions use roaming AppData paths (`%APPDATA%\.minecraft\bedrock` or `%APPDATA%\Minecraftpe`).
2. **Missing Directory Crash**: The deployment script called `fs.statSync` directly on the target path without checking for directory existence or catching `ENOENT`. On clean CI runners or systems without Minecraft pre-installed, `statSync` failed immediately.
3. **Absence of Fallback Mechanism**: If the target directory was missing, the script did not attempt recursive creation or fall back to staging files in local build output.

---

## Implementation Architecture

### 1. Dual-Runtime Path Resolution Engine
The solution delivers synchronized implementations across TypeScript/JavaScript and Python.

#### TypeScript/JavaScript Layer (`scripts/deploy.ts`, `scripts/deploy.js`, `tools/sync.js`, `tools/build.js`)
- `resolveBedrockDevPath(options)`:
  - Checks explicit overrides via CLI (`--dest`) or environment variables (`MINECRAFT_DEVELOPMENT_PATH`, `BEDROCK_DEVELOPMENT_PATH`).
  - Probes candidate locations in order:
    1. Modern Win32 Roaming Bedrock: `%APPDATA%\.minecraft\bedrock\development_<type>_packs`
    2. Roaming Minecraftpe: `%APPDATA%\Minecraftpe\games\com.mojang\...`
    3. Local Minecraftpe: `%LOCALAPPDATA%\Minecraftpe\games\com.mojang\...`
    4. UWP Store Packages: `%LOCALAPPDATA%\Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\...`
    5. macOS MCPELauncher: `~/Library/Application Support/mcpelauncher/games/com.mojang\...`
    6. Linux MCPELauncher: `~/.local/share/mcpelauncher/games/com.mojang\...`
- `deploy(options)`:
  - Traps `ENOENT` on filesystem queries.
  - Automatically provisions missing target directories with `fs.mkdirSync(target, { recursive: true })`.
  - Falls back to `dist/behavior_pack` or `dist/resource_pack` if filesystem permissions deny writing.
  - Emits non-fatal diagnostic warnings.
- `syncDirectory(source, dest, options)`:
  - Computes byte-level diffs to prevent unnecessary writes.
  - Prunes obsolete destination files and empty subdirectories.

#### Python Architecture (`packages/bedrock_deployment/`)
- `models.py`: Strongly typed enums (`PlatformType`, `PackType`) and dataclasses (`PathCandidate`, `DeploymentConfig`, `DeploymentResult`, `ResolverOptions`).
- `resolver.py`: `BedrockPathResolver` implementing OS detection, candidate generation, candidate probing, and directory provisioning.
- `validator.py`: `DeploymentValidator` ensuring safe paths (guarding against directory traversal) and validating `manifest.json` format and UUID schemas.
- `deployer.py`: `BedrockDeployer` executing differential synchronization using SHA-256 digests and safe file operations.
- `__init__.py`: Module entrypoints exporting top-level helpers `resolve_bedrock_development_path` and `deploy_pack`.

---

## Verification Results

### 1. Scoring Engine Evaluation (`scripts/score.py`)
```
==================================================
评分结果
==================================================
  correctness      40/40  Pass rate 100.0% (20/20)
  security         35/35  No violations
  quality          15/15  pylint score 10.00/10
  performance      10/10  Execution time 0.07s (baseline 1.0s)
--------------------------------------------------
  总分: 100/100   达标 
```

### 2. Pytest Test Suite (`tests/test_issue_1327.py`)
- 20 unit and integration tests passing in 0.08 seconds:
  - Windows UWP path resolution when existing
  - Windows Roaming path resolution when existing
  - Windows Roaming preference over missing UWP
  - Darwin Application Support path resolution
  - Linux local share path resolution
  - Missing directory auto-creation and ENOENT suppression
  - Fallback to local dist directory when auto-creation disabled
  - `MINECRAFT_DEVELOPMENT_PATH` and `BEDROCK_DEVELOPMENT_PATH` overrides
  - Pack type subfolder switching (`development_behavior_packs` vs `development_resource_packs`)
  - Differential synchronization and clean-slate pruning
  - Manifest validation and path safety verification

### 3. Node.js Native Test Suite (`test/deploy_path_resolution.test.js`)
- 11 test cases passing in 68ms via `node --test`:
  - Path resolution across mock environment configurations
  - Directory auto-provisioning on missing targets
  - Differential file copying and stale file deletion

---

## Payout Routing
- **EVM (Base/Arbitrum/Polygon/ETH):** `0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89`
- **Stellar:** `GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC`
