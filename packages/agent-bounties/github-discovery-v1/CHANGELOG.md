# Changelog

## [1.2.0] - 2023-XX-XX

### Fixes
- **Deterministic Agent-Card Discovery**: Restored deterministic fixture resolution in GitHub discovery v1 that was accidentally weakened in previous version. The fix ensures:
  - Consistent output for identical inputs
  - Preserved strict assertion requirements
  - Compatibility with existing discovery workflows

### Testing
- Added regression tests for deterministic behavior
- Verified pinned failing fixture now passes
- Confirmed no impact on existing functionality