# Vector DB Migration & Clean Command Enhancement

## Summary

Two major improvements were implemented:

1. **Vector Database moved to artifacts/** - Better organization and consistency
2. **Clean command enhanced** - Preserves folder structure and .gitkeep files

---

## 1. Vector Database Migration

### Before
```
SOA-CLI/
├── vector_db/              # ❌ In root directory
│   ├── index.faiss
│   └── meta.json
└── artifacts/
    ├── reader/
    ├── extracted/
    └── ...
```

### After
```
SOA-CLI/
└── artifacts/
    ├── vector_db/          # ✅ Moved to artifacts
    │   ├── .gitkeep
    │   ├── index.faiss
    │   └── meta.json
    ├── reader/
    ├── extracted/
    └── ...
```

### Why?
- **Consistency**: All generated artifacts now in one place
- **Cleaner root**: Fewer top-level directories
- **Better organization**: Easy to clean/backup all artifacts together

### Files Updated

**Code files (6 files):**
- `src/vectorize.py` - Updated paths to `artifacts/vector_db/`
- `src/similarity_cluster.py` - Updated FAISS index loading
- `src/hallucination_detector.py` - Updated vector DB loading
- `scripts/check.py` - Added `artifacts/vector_db/` to required directories

**Documentation (3 files):**
- `README.md` - Updated vector_db paths
- `docs/TOON_MIGRATION.md` - Updated metadata section
- `docs/LANGGRAPH_GUIDE.md` - Updated directory structure diagram

---

## 2. Enhanced Clean Command

### Previous Behavior ❌
```bash
python soa_cli.py --clean
```
- **Deleted entire `artifacts/` directory** 
- **Lost all folder structure**
- **Lost all .gitkeep files**
- Required manual recreation of folders

### New Behavior ✅
```bash
python soa_cli.py --clean
```
- **Deletes all artifact files**
- **Preserves all folders**
- **Preserves all .gitkeep files**
- Folders immediately ready for new run

### What Gets Cleaned

**Files deleted:**
- All `.json` files in subdirectories
- All `.tex`, `.md`, `.docx` files in soa/
- All `.faiss` files in vector_db/
- All temporary subdirectories

**Preserved:**
- All artifact folder structure
- All `.gitkeep` files (for Git tracking)
- Directory permissions and ownership

### Example Output

```
[Clean] Clearing artifact files (preserving folders and .gitkeep)...
  ✓ Cleared 48 artifact files
  ✓ Preserved folder structure and .gitkeep files
```

### Folders Cleaned

The following subdirectories are cleaned:
- `artifacts/states/` - Pipeline state files
- `artifacts/prisma/` - PRISMA reports
- `artifacts/vector_db/` - Vector database files
- `artifacts/reader/` - Per-paper parsed structures
- `artifacts/extracted/` - Per-paper extracted facts
- `artifacts/critic/` - Per-paper quality assessments
- `artifacts/clusters/` - Paper clustering outputs
- `artifacts/synthesis/` - Cross-paper synthesis
- `artifacts/soa/` - State of the Art outputs

---

## Verification

### Check Directory Structure
```bash
python scripts/check.py
```

Should show:
```
[4/7] Directory structure...
    ✓ artifacts/
    ✓ artifacts/states/
    ✓ artifacts/prisma/
    ✓ artifacts/vector_db/      ← NEW
    ✓ artifacts/reader/
    ✓ artifacts/extracted/
    ...
```

### Test Clean Command
```bash
# Before clean
find artifacts -type f | wc -l
# 48 files

python soa_cli.py --clean

# After clean
find artifacts -type f | wc -l
# 11 files (all .gitkeep)

find artifacts -name ".gitkeep" | wc -l
# 11 folders still have .gitkeep
```

---

## Git Integration

### .gitkeep Files
All artifact subdirectories now have `.gitkeep` files:
```bash
artifacts/.gitkeep
artifacts/states/.gitkeep
artifacts/prisma/.gitkeep
artifacts/vector_db/.gitkeep
artifacts/reader/.gitkeep
artifacts/extracted/.gitkeep
artifacts/critic/.gitkeep
artifacts/clusters/.gitkeep
artifacts/synthesis/.gitkeep
artifacts/soa/.gitkeep
artifacts/extracted_facts/.gitkeep
```

### Recommended .gitignore
```gitignore
# Ignore all artifact files but keep structure
artifacts/**/*
!artifacts/**/.gitkeep
!artifacts/README.md

# Specific artifacts you might want to commit
!artifacts/prisma/prisma_report.json
!artifacts/soa/state_of_the_art_final.tex
```

---

## Breaking Changes

### Code Changes Required

If you have custom scripts that reference `vector_db/`:

**Before:**
```python
index = faiss.read_index("vector_db/index.faiss")
with open("vector_db/meta.json") as f:
    meta = json.load(f)
```

**After:**
```python
index = faiss.read_index("artifacts/vector_db/index.faiss")
with open("artifacts/vector_db/meta.json") as f:
    meta = json.load(f)
```

### Migration

If you have existing `vector_db/` in root:
```bash
# Move vector_db to artifacts
mv vector_db artifacts/

# Add .gitkeep
touch artifacts/vector_db/.gitkeep
```

---

## Benefits

### Organization Benefits
✅ **All artifacts in one place** - Easy to understand where outputs go  
✅ **Consistent structure** - No exceptions for vector_db  
✅ **Easier backup** - Just tar/zip artifacts/  
✅ **Better .gitignore** - Single pattern for all artifacts

### Clean Command Benefits
✅ **Fast reset** - No need to rebuild folder structure  
✅ **Git friendly** - Preserves .gitkeep for empty folders  
✅ **Safe** - Can't accidentally delete non-artifact files  
✅ **Selective** - Only deletes generated files

### Workflow Improvements
✅ **Quick iteration** - Clean and re-run instantly  
✅ **Experiment friendly** - Easy to start fresh  
✅ **CI/CD ready** - Predictable clean state  
✅ **Debugging easier** - Clear separation of runs

---

## Usage Examples

### Fresh Run
```bash
# Clean previous artifacts
python soa_cli.py --clean

# Run pipeline
python soa_cli.py
```

### Keep Some Artifacts
```bash
# Clean everything
python soa_cli.py --clean

# But restore specific files you want to keep
# (from backup or previous run)
cp backup/artifacts/vector_db/index.faiss artifacts/vector_db/
```

### Partial Clean
```bash
# Manual selective cleaning
rm artifacts/soa/*.tex
rm artifacts/synthesis/*.json

# Or use clean command for complete reset
python soa_cli.py --clean
```

---

## Troubleshooting

### "No such file or directory" error
- **Cause**: Old code referencing `vector_db/` instead of `artifacts/vector_db/`
- **Fix**: Update your imports/paths to use `artifacts/vector_db/`

### Clean command not working
- **Cause**: Import error from missing dependencies
- **Fix**: The clean command runs early, so this shouldn't happen. Check Python version.

### Missing vector_db after migration
- **Cause**: Didn't move existing vector_db folder
- **Fix**: Run `mv vector_db artifacts/` if you have existing vector DB

---

## Future Improvements

Possible enhancements:
- Add `--clean-specific` flag to clean only certain artifact types
- Add `--preserve-vector-db` flag to keep vector DB during clean
- Add `--reset-folders` flag to delete and recreate all folders
- Add timestamped backup before clean operation

---

## Questions?

See project documentation:
- [README.md](README.md) - Main documentation
- [artifacts/README.md](artifacts/README.md) - Artifact organization guide
- [PAPER_FETCHER_GUIDE.md](PAPER_FETCHER_GUIDE.md) - Paper fetching workflow
