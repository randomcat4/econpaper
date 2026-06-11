# skill4econ Release Gate

## P0 baseline

Command:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='D:\myproject\econpaper\skill4econ\src'
conda run -n base python -m pytest tests\contracts tests\docs tests\test_skill_docs_contract.py -q
```

Result:

- `29 passed`
- `4 warnings`

Warnings:

- `datetime.utcnow()` deprecation warning in `src/skill4econ/core.py`
- `requests` dependency warning from the active conda environment

Interpretation:

The focused contract/docs baseline is green. The first roadmap fixes can focus
on EasyPaper Phase A1 before expanding skill4econ smoke coverage.

