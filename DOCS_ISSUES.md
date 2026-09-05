# Documentation Issues Found

> Historical audit: these findings describe an earlier documentation snapshot, and some have been resolved. This is not a current issue tracker. See the [documentation index](DOCS_INDEX_en.md) and [technical reference](TECHNICAL_REFERENCE.md) for current guidance.

## Missing Files & Broken References

### 1. Broken Link in DOCS_INDEX.md
- **Issue**: References `tools/ASAR_CLI.md` which doesn't exist
- **Location**: Line 33 in DOCS_INDEX.md
- **Impact**: Broken link in documentation index

### 2. Incomplete UTILS_GUIDE.md
- **Issue**: Missing documentation for 4 utility modules
- **Missing modules**:
  - `disk_utils.py` - Disk space and file size utilities
  - `operation_lock.py` - Threading and operation synchronization
  - `platform.py` - Platform-specific utilities
  - `transaction.py` - Transaction management for file operations
- **Impact**: Incomplete developer reference

### 3. Outdated PROJECT_SPECS.md
- **Issue**: May not reflect recent architectural changes
- **Last verified**: Need to compare with actual codebase structure
- **Impact**: Potential confusion for new developers

## Content Mismatches

### 1. Directory Structure
- **PROJECT_SPECS.md** lists modules that may have been reorganized
- **UTILS_GUIDE.md** doesn't cover all 15 utility files
- **DOCS_INDEX.md** references non-existent tools directory

### 2. API Documentation
- **API_DOCS.md** appears auto-generated - needs verification against actual code
- May be missing new functions or have outdated signatures

## Recommendations

### Immediate Fixes
1. **Remove broken reference** to `tools/ASAR_CLI.md` from DOCS_INDEX.md
2. **Update UTILS_GUIDE.md** to include missing utility modules
3. **Verify PROJECT_SPECS.md** against current architecture

### Medium-term Improvements
1. **Add missing guides** for disk_utils, operation_lock, platform, transaction modules
2. **Create ASAR_CLI.md** or remove reference if functionality moved elsewhere
3. **Regenerate API_DOCS.md** if it's auto-generated

### Quality Assurance
1. **Cross-reference check**: Ensure all files mentioned in docs exist
2. **Completeness audit**: Verify all public APIs are documented
3. **Consistency check**: Ensure all README variants (CN/EN/JP) are synchronized