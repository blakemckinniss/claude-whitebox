# Groq.py Usage Examples

## Basic Chat Completion

```bash
# Simple question
groq.py "What is quantum computing?"

# With custom model
groq.py --model "llama-3.3-70b-versatile" "Explain async/await in Python"

# Higher temperature for creativity
groq.py --temperature 0.9 "Write a haiku about code"
```

## Web Search (Built-in Tool)

```bash
# Real-time web search
groq.py --web-search "Latest AI developments 2025"

# With compound model (optimized for tools)
groq.py --model "groq/compound" --web-search "Current price of Bitcoin"
```

## URL Grounding (visit_website)

```bash
# Summarize article
groq.py --url https://example.com/article "Summarize this article"

# Extract specific information
groq.py --url https://docs.python.org/3/library/asyncio.html "Explain asyncio.gather"
```

## Streaming Response

```bash
# Stream output as it generates
groq.py --stream "Write a short story about an AI"

# Stream with web search
groq.py --stream --web-search "Latest news on quantum computing"
```

## Custom System Prompts

```bash
# Act as expert
groq.py --system "You are a senior Rust engineer" "Review this code pattern"

# Specialized persona
groq.py --system "You are a security researcher. Be critical and paranoid." "Audit this auth flow"
```

## Advanced Usage

```bash
# High token limit for long responses
groq.py --max-tokens 8192 "Write a comprehensive guide to Python async"

# Low temperature for factual answers
groq.py --temperature 0.2 "What is the capital of France?"

# Combine multiple features
groq.py --model "llama-3.3-70b-versatile" \
        --web-search \
        --temperature 0.7 \
        --max-tokens 2048 \
        "Research the latest AI research papers and summarize key findings"
```

## Tool Features

### Available Models
- `moonshotai/kimi-k2-instruct-0905` (default, 128k context)
- `llama-3.3-70b-versatile` (128k context)
- `groq/compound` (multi-tool optimized)

### Built-in Tools
- `web_search`: Real-time web search capability
- `visit_website`: URL content grounding

### Parameters
- `--temperature`: Sampling temperature 0-2 (default: 0.6)
- `--max-tokens`: Maximum completion tokens (default: 4096)
- `--stream`: Enable streaming output
- `--web-search`: Enable web search tool
- `--url`: URL to ground response with
- `--system`: Custom system prompt

## Zero Dependencies

Uses stdlib only:
- `urllib.request`: HTTP requests
- `json`: Response parsing
- `scripts/lib/core.py`: Shared utilities

No external libraries required!
