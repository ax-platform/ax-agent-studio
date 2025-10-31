# Bug Report: Triple Backtick Code Blocks Cause Message Truncation

## Summary
Messages containing triple backtick (```) code blocks get truncated when sent from agents. The truncation occurs at or before the code block, cutting off all content that follows.

## Reproduction Steps
1. Send a message to an agent that contains a triple backtick code block
2. Example:
   ```
   @agent Testing code block:

   ```
   code here
   ```

   Did you see the code above?
   ```
3. The receiving agent only sees: "@agent Testing code block:" and nothing after

## What Works
- ✅ Plain text messages
- ✅ Single backtick inline code: `code`
- ✅ Forward slashes with spaces: `before / after`
- ✅ File paths without backticks: `src/ax_agent_studio/file.py`
- ✅ Backtick-wrapped paths: `` `src/file.py` ``

## What Doesn't Work
- ❌ Triple backtick code blocks (` ``` `)
- ❌ Multi-line code examples
- ❌ Any content after triple backticks

## Impact
- Agents cannot share code snippets with each other
- Documentation and debugging are severely limited
- File paths in initial messages got truncated because they were in code blocks

## Investigation Results
- Searched entire `src/ax_agent_studio/` codebase
- Found NO code that parses or handles triple backticks
- No markdown processing, fence detection, or code block logic in our code
- Bug appears to be in **Claude Agent SDK** (v0.1.5 - latest version as of Oct 2025)
- Confirmed using latest SDK version: `claude-agent-sdk==0.1.5`

## Tested Agents
- Aurora (Claude Code SDK) - **AFFECTED** ❌
- sleek_orion_547 (Claude Code SDK) - **AFFECTED** ❌
- HaloScript (LangGraph) - **NOT AFFECTED** ✅

## Conclusion
**This is a Claude Code SDK-specific bug.** LangGraph agents receive code blocks without any truncation.

## Workarounds
1. Use 4-space indentation instead of code fences
2. Use single backticks for inline code only
3. Send code line-by-line without formatting
4. Describe code instead of pasting it

## Next Steps
1. Test with non-Claude Code agents (LangGraph, Ollama, Echo)
2. Report to Anthropic if confirmed as Claude Code SDK bug
3. Add preprocessing to escape/handle code blocks if needed

## Date Identified
2025-10-30

## Severity
**Medium** - Limits agent collaboration but workarounds exist
