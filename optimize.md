# Optimization Notes

## api/api_chats.py
- Duplicated imports and repeated sys.path mutations clutter the top of the file; extract a single import section and move path configuration into a shared loader or remove if package layouts are fixed.
- Chat orchestration, RAG fetch, and HTTP layer are intertwined in the same route functions; pull RAG/query rewrite/run logic into a service class to simplify the Blueprint to I/O and error handling only.
- Mixing sync and async helpers (`asyncio.run` for reads, sync writes) risks blocking the event loop and makes testing hard; standardize on async or sync and expose thin adapters per route.
- Utility functions like `_epoch_to_human`, `_normalize_rag_rows`, and `split_text_into_chunks` are defined inline; lift into a module so both Flask and FastAPI implementations share the same helpers.

## LLM_calls/context_manager.py
- Redundant sys.path manipulation appears twice and is copy-pasted across other modules; replace with proper package initialization and relative imports, or a single bootstrap module.
- Conversation memory setup, prompt construction, and streaming are tightly coupled; consider a `LLMClient` wrapper that accepts a prompt builder and stream client to improve testability and reduce logging noise (`print` tokens in production logs).
- Uses globals for `system_prompt`; move prompts to configuration and inject per call to better support multi-tenant or environment-specific tuning.

## utlis/utlis_functions.py
- Multiple repeated `import re` statements and large commented "example usage" blocks bloat the utility module; prune duplicates and move runnable examples into tests or docs.
- Functions with overlapping behavior (`extract_python_code`, `extract_code_block`) diverge in patterns; consolidate into a single, well-tested extractor that accepts language + fallback handling.
- Error handling currently prints and swallows exceptions (`extract_json_from_string`); return structured errors or raise to allow callers to surface failures.
- The filename-to-language map is hardcoded and large; consider moving to a data file or using a library (e.g., `pygments`) to avoid manual maintenance.

## Octave_mem/RAG_DB_CONTROLLER/read_data_RAG_all_DB.py
- Path hacks and environment bootstrapping are repeated; convert `Octave_mem` and `backend_examples` into installable packages and rely on relative imports to remove sys.path edits.
- Reader mixes Chroma retrieval with Supabase profile CRUD methods; split into separate concern-specific classes (RAG reader vs. profile store) to avoid pulling Supabase deps into every vector read.
- Async profile methods coexist with sync RAG queries, and some return `None` vs. lists interchangeably; standardize return types, add type guards, and extract an interface for async callers.
- Inline `print` debugging is extensive; replace with structured logging or proper exceptions so downstream services can decide how to handle failures.

## Cross-cutting
- Create a shared bootstrap/utilities module for path resolution and logging to eliminate copy-paste across `api/`, `LLM_calls/`, and `Octave_mem/`.
- Add unit tests around the parsing utilities and RAG readers to lock behavior before refactoring; current example comments indicate manual testing only.
