"""Heuristic constants used by the Website Crawler service."""

CRAWLER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 AIGeoCopilotBot/1.0"
)

NAVIGATION_TIMEOUT_MS = 20_000
MAX_FETCH_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1.0
POLITENESS_DELAY_SECONDS = 1.5

# Link text/href substrings used to discover an FAQ/Help page and a Blog
# page from the homepage navigation. Order matters - first match wins.
FAQ_LINK_HINTS = ["faq", "frequently asked", "help", "support", "help-center", "help center"]
BLOG_LINK_HINTS = ["blog", "news", "articles", "insights"]

# Heading text ending in "?" is treated as a candidate FAQ entry. Elements
# whose class/id contain any of these substrings are also treated as
# FAQ/accordion patterns.
FAQ_ELEMENT_CLASS_HINTS = ["faq", "accordion", "toggle-content", "qa-item", "question"]

# Known schema.org @type values we specifically look out for (still records
# any other @type found - this list is just used for logging/summary, not
# filtering).
KNOWN_SCHEMA_TYPES_OF_INTEREST = [
    "Organization",
    "Product",
    "SoftwareApplication",
    "FAQPage",
    "Article",
    "BreadcrumbList",
    "WebSite",
    "LocalBusiness",
    "Review",
    "AggregateRating",
]

MAX_HEADINGS_PER_LEVEL = 15
