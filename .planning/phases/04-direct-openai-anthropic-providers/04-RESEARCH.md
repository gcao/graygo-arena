# Phase 4 Research: Direct Provider Adapters

**Researched:** 2026-04-25
**Sources:** Official OpenAI and Anthropic documentation.

## OpenAI

OpenAI's Responses API supports structured outputs by setting a JSON Schema format on the response text. The docs describe `text.format` with `type: "json_schema"`, `name`, `schema`, and optional `strict`. Responses also support `previous_response_id` for conversation state, but Phase 4 should keep each seat's state separate and can begin statelessly.

Implementation:

- POST `https://api.openai.com/v1/responses`
- Header `Authorization: Bearer $OPENAI_API_KEY`
- Header `Content-Type: application/json`
- Body includes `model`, `input`, `max_output_tokens`, and `text.format`
- Parse `output_text` or content text blocks as JSON.

## Anthropic

Anthropic's Messages API requires `x-api-key`, `anthropic-version`, and `content-type` headers. The API is stateless; the caller sends message history. Tool use accepts client tool definitions with `name`, `description`, and `input_schema`; a forced `tool_choice` can require the move-selection tool.

Implementation:

- POST `https://api.anthropic.com/v1/messages`
- Header `x-api-key: $ANTHROPIC_API_KEY`
- Header `anthropic-version: 2023-06-01`
- Header `content-type: application/json`
- Body includes `model`, `max_tokens`, `system`, `messages`, `tools`, and `tool_choice`
- Parse the `tool_use` block named `choose_graygo_move`.

## Shared Move Schema

Use the same schema for both providers:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["board_key", "move", "strategic_summary"],
  "properties": {
    "board_key": {"type": "string"},
    "move": {"type": "string"},
    "strategic_summary": {"type": "string"}
  }
}
```

The orchestrator still validates BoardKey and legal move; provider structured output is only a parsing constraint.

## Verification

Add tests that:

- assert OpenAI request payload uses `json_schema`
- assert Anthropic request payload uses forced tool choice
- parse mocked successful responses
- surface missing keys as safe provider-test failures
- verify provider catalog exposes aliases without token values

---

*Research completed: 2026-04-25*
