"""Heuristic constants used by the Play Store Analyzer service."""

MAX_FETCH_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1.0
FETCH_TIMEOUT_SECONDS = 20.0
REVIEWS_TO_FETCH = 100

# Simple, hand-picked category -> keyword heuristic lists. Not exhaustive -
# meant only to give a rough "does the listing mention category-relevant
# terms" signal, no AI/embedding involved.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "productivity": ["task", "productivity", "organize", "efficient", "workflow", "schedule"],
    "finance": ["money", "bank", "payment", "budget", "invest", "wallet", "transaction"],
    "social": ["chat", "message", "friend", "connect", "share", "community", "profile"],
    "health": ["health", "fitness", "workout", "diet", "wellness", "sleep", "medical"],
    "education": ["learn", "course", "lesson", "study", "quiz", "teacher", "student"],
    "shopping": ["shop", "cart", "discount", "deal", "order", "delivery", "price"],
    "travel": ["travel", "flight", "hotel", "booking", "trip", "itinerary", "map"],
    "entertainment": ["watch", "stream", "video", "music", "game", "play", "movie"],
}

GENERIC_KEYWORDS = ["free", "easy", "fast", "secure", "simple", "best", "new", "offline"]
