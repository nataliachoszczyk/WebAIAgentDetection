# The browser agent

The agent does the four shop tasks through a model API. Its sessions are the agent traces of the study.

## Access to the models (wad-007)

Decision: the agent uses the OpenRouter key from the course. The Kaggle Model Proxy is the second option.

| Option | Limit | Where it works |
|---|---|---|
| OpenRouter (`https://openrouter.ai/api/v1`) | 35 USD for the full project | everywhere: laptop, Kaggle kernel, Kaggle Benchmark Task |
| Kaggle Model Proxy | 10 USD for each day, 100 USD for each month | only in a Kaggle Benchmark Task of the account `nataliachoszczyk` |

- The key is `OPENROUTER_API_KEY` in the local `.env`. On Kaggle, keep it in Kaggle Secrets.
- `src/agent/model.py` calls both APIs with the same code (`Model(..., api="openrouter")` or `api="kaggle"`).
- `spend()` in the same file gives the spend of the key. The value changes some minutes after a request.
- Each answer gives its cost in USD (`usage.cost` of OpenRouter). The agent writes it into the step log.

Check of the access (2026-11-28): each model read a screenshot, called a tool and used the effort `medium`.

| Model id | Input (USD for 1M tokens) | Output (USD for 1M tokens) | Answer time |
|---|---|---|---|
| `anthropic/claude-haiku-5.5` | 0.10 | 0.50 | 1.8 s |
| `anthropic/claude-sonnet-5.5` | 2.00 | 10.00 | 1.1 s |
| `anthropic/claude-opus-5.5` | 4.00 | 20.00 | 2.1 s |

The thoughts of the model are output tokens. OpenRouter gives them back in `reasoning_details`. The agent sends them back with the next request, so that the model keeps them between tool calls.

Plan for the costs:

1. Develop and test the agent with a scripted model, without the API.
2. Use `claude-haiku-5.5` for the first real runs. One run costs some cents.
3. Use `claude-sonnet-5.5`, then `claude-opus-5.5`, only after the Haiku runs work without errors.
4. Check the spend before and after each group of runs.
