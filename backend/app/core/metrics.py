from prometheus_client import Counter, Histogram, Gauge

# ── HTTP ──
HTTP_REQUESTS_TOTAL = Counter(
    "quizhub_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "quizhub_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Game rooms ──
ACTIVE_ROOMS = Gauge(
    "quizhub_active_rooms",
    "Number of currently active game rooms",
)
GAMES_STARTED_TOTAL = Counter(
    "quizhub_games_started_total",
    "Total number of games started",
)
GAMES_FINISHED_TOTAL = Counter(
    "quizhub_games_finished_total",
    "Total number of games finished",
)

# ── Players ──
ACTIVE_PLAYERS = Gauge(
    "quizhub_active_players",
    "Number of currently connected players across all rooms",
)
PLAYERS_JOINED_TOTAL = Counter(
    "quizhub_players_joined_total",
    "Total number of player joins",
)

# ── Answers ──
ANSWERS_TOTAL = Counter(
    "quizhub_answers_total",
    "Total answers submitted",
    ["correct"],
)
ANSWER_TIME_SECONDS = Histogram(
    "quizhub_answer_time_seconds",
    "Time taken by a player to answer a question",
    buckets=[1, 2, 3, 5, 8, 10, 15, 20, 30],
)

# ── WebSocket ──
WS_CONNECTIONS_TOTAL = Counter(
    "quizhub_ws_connections_total",
    "Total WebSocket connections",
    ["role"],  # host | player
)
WS_DISCONNECTIONS_TOTAL = Counter(
    "quizhub_ws_disconnections_total",
    "Total WebSocket disconnections",
    ["role"],
)
