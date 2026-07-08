"""Heuristic constants for the Review Intelligence agent."""

# Target batch size (reviews per LLM call).
TARGET_BATCH_SIZE = 45
MIN_BATCH_SIZE = 10
MAX_BATCH_SIZE = 50

# Conservative token budget: ~4 characters per token, cap input at ~6000 tokens
# for the review text portion (leaves room for system prompt + JSON output).
MAX_BATCH_INPUT_TOKENS = 6000
CHARS_PER_TOKEN_ESTIMATE = 4
