# Context Collector Formatting Guide

This document describes the standard markdown format used by context collectors when building context for LLM prompts.

## Standard Context Format

All context collectors output markdown-formatted text following these conventions:

### Document Structure

```markdown
# Main Heading

Brief description or metadata about the context.

## Section Heading

Content for this section.

### Subsection Heading

More specific content.
```

### Code Block Format

Code content is wrapped in fenced code blocks with language hints:

```markdown
## path/to/file.py

```python
def example():
    pass
```
```

The language hint after the opening fence should match the file extension:
- `.py` → `python`
- `.js` → `javascript`
- `.ts` → `typescript`
- `.json` → `json`
- `.yaml`, `.yml` → `yaml`
- `.md` → `markdown`
- `.sh` → `bash`

### File Content Pattern

When including file contents, use this pattern:

```markdown
## relative/path/to/file.ext

```language
<file contents here>
```
```

For files that don't exist or can't be read:

```markdown
## relative/path/to/file.ext

*File not found*
```

Or for read errors:

```markdown
## relative/path/to/file.ext

```
[Error reading file: <error message>]
```
```

### Diff Format

For git diffs, use the `diff` language hint:

```markdown
## Git Diff

```diff
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 existing line
+added line
-removed line
 unchanged line
```
```

### Before/After Pattern

When showing file changes (initial vs final states):

```markdown
### path/to/file.py

#### Initial

```python
<original content>
```

#### Final

```python
<modified content>
```
```

For newly added files:
```markdown
#### Initial

*File did not exist (newly added)*
```

For deleted files:
```markdown
#### Final

*File was deleted*
```

## Collector Modules

### `pr.py`
Collects PR context including:
- Git diff
- File changes (initial/final states)

### `file_category.py`
Collects file listing for LLM categorization:
- Respects .gitignore patterns
- Lists all files for categorization as `test`, `app`, or `infra`

### `repo.py`
Collects repository file contents:
- `repo()`: Builds context from a list of file paths
- `structure()`: Builds context showing file organization by category

## Usage Example

```python
from crev.utils.context.collector import pr, file_category
from crev.utils.context.collector.repo import repo, structure

# Collect PR context
pr_context = pr(pr_directory)

# Collect files for categorization
categorization_context = file_category(repo_path)

# Collect app files context
app_context = repo(repo_path, app_files, category="app")

# Collect structure summary
structure_context = structure({
    "app": app_files,
    "test": test_files,
    "infra": infra_files,
})
```
