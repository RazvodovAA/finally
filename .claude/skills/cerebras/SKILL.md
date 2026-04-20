---
name: cerebras
description: Use this to write code to call an LLM using LiteLLM and OpenAI 
---

# Calling an LLM

These instructions allow you write code to call an LLM.  
This method uses LiteLLM and OpenAI.

## Setup

The OPENAI_API_KEY must be set in the .env file and loaded in as an environment variable.  

The uv project must include litellm and pydantic.
`uv add litellm pydantic`

### Imports and constants

```python
from litellm import completion
MODEL = "openai/gpt-4"
```

### Code to call the LLM for a standard response

```python
response = completion(model=MODEL, messages=messages, reasoning_effort="low", extra_body=EXTRA_BODY)
result = response.choices[0].message.content
```

### Code to call the LLM for a Structured Outputs response

```python
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass, reasoning_effort="low", extra_body=EXTRA_BODY)
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```