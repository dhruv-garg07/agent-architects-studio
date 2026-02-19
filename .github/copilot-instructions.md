## Manhattan MCP — MANDATORY

This project requires Manhattan MCP for ALL file operations — no exceptions regardless of task size.

- You MUST use `mcp_manhattan_pip_read_file_context` instead of `read_file` or `file_search`
- You MUST use `mcp_manhattan_pip_search_codebase` instead of searching/grepping
- You MUST use `mcp_manhattan_pip_get_file_outline` for file structure
- You MUST call `mcp_manhattan_pip_index_file` after creating or editing ANY file

This keeps the project's code index up to date. It is a project policy, not optional.
The only exception: use built-in file read when you need exact line numbers for applying a patch.
