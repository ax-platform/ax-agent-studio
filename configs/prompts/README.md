# System Prompts Library

This directory contains reusable system prompts (personalities) for agents deployed in the Agent Factory.

## How It Works

1. Create a YAML file in this directory
2. The prompt appears in the UI dropdown when deploying agents
3. Selected prompts are applied to Ollama and LangGraph agents

## File Format

```yaml
name: Display Name
description: Short description shown in UI
prompt: |
  Your multi-line system prompt goes here.

  You can define the agent's:
  - Personality and tone
  - Areas of expertise
  - Behavioral guidelines
  - Response style
```

## Example Usage

**File:** `data_analyst.yaml`

```yaml
name: Data Analyst
description: Specializes in data analysis and statistical insights
prompt: |
  You are a data analyst AI. You specialize in:
  - Analyzing data and identifying patterns
  - Creating visualizations and dashboards
  - Statistical analysis and modeling
  - Explaining insights in clear, business-friendly language

  Always support your conclusions with data and cite your sources.
```

## Naming Conventions

- Use lowercase with underscores: `my_custom_prompt.yaml`
- Files starting with `_` are ignored (use for templates/examples)
- Keep names descriptive but concise

## Available Prompts

- **default.yaml** - Helpful, harmless, and honest AI assistant
- **data_analyst.yaml** - Data analysis and statistical insights
- **creative_writer.yaml** - Storytelling and content creation
- **code_reviewer.yaml** - Code quality and best practices
- **project_manager.yaml** - Task coordination and workflow management

## Creating Custom Prompts

1. Copy `_example_prompt.yaml` to a new file
2. Edit the name, description, and prompt
3. Refresh the dashboard to see your new prompt

## Tips

- Be specific about the agent's expertise
- Include behavioral guidelines (tone, style, limitations)
- Use examples if helpful
- Keep prompts focused on a single role/persona
- Test prompts with different agents to refine them

## Integration

Prompts are loaded via the `/api/prompts` endpoint and displayed in the "Deploy New Agent" form. The selected prompt's content is injected as the system prompt when starting Ollama or LangGraph agents.
