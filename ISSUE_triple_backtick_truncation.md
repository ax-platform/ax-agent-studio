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
-  Plain text messages
-  Single backtick inline code: `code`
-  Forward slashes with spaces: `before / after`
-  File paths without backticks: `src/ax_agent_studio/file.py`
-  Backtick-wrapped paths: `` `src/file.py` ``

## What Doesn't Work
-  Triple backtick code blocks (` ``` `)
-  Multi-line code examples
-  Any content after triple backticks

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
- Aurora (Claude Code SDK) - **AFFECTED** 
- sleek_orion_547 (Claude Code SDK) - **AFFECTED** 
- HaloScript (LangGraph) - **NOT AFFECTED** 

## Conclusion
**This is a Claude Code SDK-specific bug.** LangGraph agents receive code blocks without any truncation.

## Workarounds
1. Use 4-space indentation instead of code fences
2. Use single backticks for inline code only
3. Send code line-by-line without formatting
4. Describe code instead of pasting it

## Fix Implemented
**Status: FIXED locally** (2025-10-30)

Added `_fix_code_blocks()` function in `claude_agent_sdk_monitor.py` that:
1. Detects triple backtick code blocks in messages
2. Converts them to 4-space indented format
3. Preserves language hints as "Code (lang):" prefix
4. Applied to **BOTH incoming AND outgoing messages**
   - Incoming: Preprocessed before Claude SDK processes them
   - Outgoing: Converted before sending responses

This allows Claude Agent SDK agents to both SEND and RECEIVE code examples without triggering the MCP transport truncation bug.

**Testing:**  Confirmed working with Aurora
- Outgoing: Aurora's responses with code blocks transmit fully
- Incoming: Messages TO Aurora with code blocks are received completely

## Next Steps
1.  ~~Test with non-Claude Code agents~~ - Confirmed LangGraph not affected
2. Report upstream to Anthropic (SDK bug remains in v0.1.5)
3.  ~~Add preprocessing to escape/handle code blocks~~ - DONE

## Date Identified
2025-10-30

## Date Fixed
2025-10-30

## Severity
**Low** - Fixed locally with automatic workaround
