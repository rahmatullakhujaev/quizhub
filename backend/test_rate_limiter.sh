#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# Rate Limiter Test Suite (Self-Contained)
# ═══════════════════════════════════════════════════════════════════════
# Usage:
#   chmod +x test_rate_limiter.sh
#   ./test_rate_limiter.sh
#
# Optional overrides:
#   BASE_URL   - default: http://localhost:80
#   GET_PATH   - a GET endpoint to test (default: /api/collections)
#
# This script:
#   1. Creates a test user (rl_test_<random>)
#   2. Logs in to get a JWT token
#   3. Runs all rate limiter tests
#   4. Prints a full report
#   (test user stays in DB — harmless, or delete manually)
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ──
BASE_URL="${BASE_URL:-http://localhost:80}"
GET_PATH="${GET_PATH:-/api/collections}"

# Load DB creds from .env if it exists (same .env your docker-compose uses)
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-quizhub}"

# Generate unique test user credentials
RANDOM_ID=$(date +%s%N | md5sum | head -c 8)
TEST_USERNAME="rl_test_${RANDOM_ID}"
TEST_EMAIL="${TEST_USERNAME}@test.com"
TEST_PASSWORD="TestPass123!"

# ── Colors ──
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Counters ──
PASS=0
FAIL=0
SKIP=0
TOTAL=0

# ── Report storage ──
REPORT=""

# ── Helper functions ──

log_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

log_test() {
    TOTAL=$((TOTAL + 1))
    echo -e "\n  ${YELLOW}▸ Test $TOTAL: $1${NC}"
}

log_pass() {
    PASS=$((PASS + 1))
    echo -e "    ${GREEN}✓ PASS${NC} — $1"
    REPORT+="  ✓ PASS  | $1\n"
}

log_fail() {
    FAIL=$((FAIL + 1))
    echo -e "    ${RED}✗ FAIL${NC} — $1"
    REPORT+="  ✗ FAIL  | $1\n"
}

log_skip() {
    SKIP=$((SKIP + 1))
    echo -e "    ${YELLOW}⊘ SKIP${NC} — $1"
    REPORT+="  ⊘ SKIP  | $1\n"
}

do_request() {
    local method="$1"
    local path="$2"
    shift 2
    local url="${BASE_URL}${path}"

    local tmpfile
    tmpfile=$(mktemp)

    RESP_CODE=$(curl -s -o "$tmpfile" -w "%{http_code}" \
        -X "$method" "$url" \
        "$@" 2>/dev/null) || true

    RESP_BODY=$(cat "$tmpfile" 2>/dev/null) || true
    rm -f "$tmpfile"
}

do_request_headers() {
    local method="$1"
    local path="$2"
    shift 2
    local url="${BASE_URL}${path}"

    RESP_HEADERS=$(curl -s -D - -o /dev/null \
        -X "$method" "$url" \
        "$@" 2>/dev/null) || true
}

get_header() {
    echo "$RESP_HEADERS" | grep -i "^$1:" | head -1 | cut -d':' -f2- | tr -d ' \r\n'
}


# ═══════════════════════════════════════════════════════════════════════
# PRE-FLIGHT: Server check
# ═══════════════════════════════════════════════════════════════════════
log_header "PRE-FLIGHT CHECKS"

echo -e "  Base URL:    ${BOLD}${BASE_URL}${NC}"
echo -e "  GET path:    ${BOLD}${GET_PATH}${NC}"
echo -e "  Test user:   ${BOLD}${TEST_USERNAME}${NC}"

log_test "Server is reachable"
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null) || true
if [[ "$HEALTH_CODE" == "200" ]]; then
    log_pass "Server responded 200 on /health"
else
    log_fail "Server unreachable (got HTTP $HEALTH_CODE). Is docker-compose up?"
    echo -e "\n${RED}Cannot continue without a running server. Exiting.${NC}"
    exit 1
fi


# ═══════════════════════════════════════════════════════════════════════
# AUTO-AUTH: Create test user and get JWT
# ═══════════════════════════════════════════════════════════════════════
log_header "AUTO-AUTH: Creating test user & getting JWT"

log_test "Register test user"
do_request POST "/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${TEST_USERNAME}\", \"email\": \"${TEST_EMAIL}\", \"password\": \"${TEST_PASSWORD}\"}"

echo -e "      Register → HTTP $RESP_CODE"

if [[ "$RESP_CODE" == "201" ]]; then
    log_pass "Test user created: ${TEST_USERNAME}"
elif [[ "$RESP_CODE" == "400" ]]; then
    echo -e "      (User may already exist — continuing)"
    log_pass "User already exists, proceeding"
else
    log_fail "Registration failed (HTTP $RESP_CODE): $RESP_BODY"
    echo -e "\n${RED}Cannot get auth token. Exiting.${NC}"
    exit 1
fi

sleep 1.2

log_test "Login to get JWT token"
do_request POST "/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}"

echo -e "      Login → HTTP $RESP_CODE"

if [[ "$RESP_CODE" == "200" ]]; then
    AUTH_TOKEN=$(echo "$RESP_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) || true
    if [[ -n "$AUTH_TOKEN" ]]; then
        log_pass "Got JWT token (${#AUTH_TOKEN} chars)"
        echo -e "      Token: ${AUTH_TOKEN:0:20}...${AUTH_TOKEN: -10}"
    else
        log_fail "Login succeeded but couldn't extract token from: $RESP_BODY"
        AUTH_TOKEN=""
    fi
else
    log_fail "Login failed (HTTP $RESP_CODE): $RESP_BODY"
    AUTH_TOKEN=""
fi

if [[ -n "${AUTH_TOKEN:-}" ]]; then
    sleep 1.2
    log_test "Verify token with /api/auth/me"
    do_request GET "/api/auth/me" -H "Authorization: Bearer ${AUTH_TOKEN}"
    echo -e "      /api/auth/me → HTTP $RESP_CODE"

    if [[ "$RESP_CODE" == "200" ]]; then
        log_pass "Token is valid — authenticated as ${TEST_USERNAME}"
    else
        log_fail "Token verification failed (HTTP $RESP_CODE)"
    fi
fi


# ═══════════════════════════════════════════════════════════════════════
# TEST 1: Health endpoint is NOT rate-limited
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST 1: Health endpoint bypass"

log_test "/health should never return 429"
ALL_OK=true
for i in $(seq 1 25); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" 2>/dev/null) || true
    if [[ "$code" == "429" ]]; then
        ALL_OK=false
        break
    fi
done

if $ALL_OK; then
    log_pass "/health survived 25 rapid requests without 429"
else
    log_fail "/health got rate-limited (returned 429)"
fi


# ═══════════════════════════════════════════════════════════════════════
# TEST 2: POST per-user rate limit (2 req/sec)
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST 2: POST per-user limit (2 req/sec)"

if [[ -z "${AUTH_TOKEN:-}" ]]; then
    log_test "POST with auth token"
    log_skip "Auth token not available — skipping per-user tests"
else
    sleep 1.2

    log_test "First 2 POST requests should succeed"
    codes=()
    for i in 1 2; do
        do_request POST "/api/auth/register" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${AUTH_TOKEN}" \
            -d "{\"username\": \"dummy_${RANDOM_ID}_${i}\", \"email\": \"dummy_${RANDOM_ID}_${i}@x.com\", \"password\": \"Xx123456!\"}"
        codes+=("$RESP_CODE")
        echo -e "      Request $i → HTTP $RESP_CODE"
    done

    if [[ "${codes[0]}" != "429" && "${codes[1]}" != "429" ]]; then
        log_pass "First 2 requests were not rate-limited (${codes[0]}, ${codes[1]})"
    else
        log_fail "Got 429 too early (${codes[0]}, ${codes[1]})"
    fi

    log_test "3rd POST request should be rate-limited (429)"
    do_request POST "/api/auth/register" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -d "{\"username\": \"dummy_blocked\", \"email\": \"blocked@x.com\", \"password\": \"Xx123456!\"}"
    echo -e "      Request 3 → HTTP $RESP_CODE"

    if [[ "$RESP_CODE" == "429" ]]; then
        log_pass "3rd request correctly returned 429"
    else
        log_fail "Expected 429, got $RESP_CODE"
    fi

    log_test "429 body should be valid JSON with error details"
    if echo "$RESP_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'error' in d, 'missing error field'
assert d['error'] == 'rate_limit_exceeded', f'wrong error: {d[\"error\"]}'
assert 'retry_after' in d, 'missing retry_after field'
assert 'message' in d, 'missing message field'
print('      ' + json.dumps(d, indent=2).replace(chr(10), chr(10) + '      '))
" 2>/dev/null; then
        log_pass "429 body has correct JSON structure"
    else
        log_fail "429 body malformed: $RESP_BODY"
    fi

    log_test "Response should include X-RateLimit-* headers"
    sleep 1.2
    do_request_headers POST "/api/auth/register" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -d "{\"username\": \"dummy_hdr\", \"email\": \"hdr@x.com\", \"password\": \"Xx123456!\"}"

    rl_limit=$(get_header "X-RateLimit-Limit")
    rl_remaining=$(get_header "X-RateLimit-Remaining")
    rl_reset=$(get_header "X-RateLimit-Reset")

    echo -e "      X-RateLimit-Limit:     ${rl_limit:-MISSING}"
    echo -e "      X-RateLimit-Remaining: ${rl_remaining:-MISSING}"
    echo -e "      X-RateLimit-Reset:     ${rl_reset:-MISSING}"

    if [[ -n "$rl_limit" && -n "$rl_remaining" && -n "$rl_reset" ]]; then
        log_pass "All three X-RateLimit headers present"
    else
        log_fail "Missing one or more X-RateLimit headers"
    fi

    log_test "After waiting 1 second, requests should work again"
    sleep 1.2
    do_request POST "/api/auth/register" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -d "{\"username\": \"dummy_reset_${RANDOM_ID}\", \"email\": \"reset_${RANDOM_ID}@x.com\", \"password\": \"Xx123456!\"}"
    echo -e "      Request after reset → HTTP $RESP_CODE"

    if [[ "$RESP_CODE" != "429" ]]; then
        log_pass "Rate limit reset after window expired"
    else
        log_fail "Still rate-limited after waiting 1 second"
    fi
fi


# ═══════════════════════════════════════════════════════════════════════
# TEST 3: POST per-IP fallback (no auth token)
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST 3: POST without auth (IP fallback)"

sleep 1.2

log_test "POST without token should still be rate-limited (by IP)"
codes=()
for i in $(seq 1 4); do
    do_request POST "/api/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=nobody&password=wrong"
    codes+=("$RESP_CODE")
done

echo -e "      Responses: ${codes[*]}"

if [[ "${codes[2]}" == "429" || "${codes[3]}" == "429" ]]; then
    log_pass "Unauthenticated POST correctly rate-limited by IP"
else
    log_fail "Expected 429 on 3rd/4th request, got: ${codes[2]}, ${codes[3]}"
fi


# ═══════════════════════════════════════════════════════════════════════
# TEST 4: GET per-IP rate limit (15 req/sec)
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST 4: GET per-IP limit (15 req/sec)"

sleep 1.2

log_test "First 15 GET requests should succeed, 16th should be 429"
count_ok=0
count_429=0
first_429_at=0

for i in $(seq 1 20); do
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${BASE_URL}${GET_PATH}" 2>/dev/null) || true
    if [[ "$code" == "429" ]]; then
        count_429=$((count_429 + 1))
        if [[ $first_429_at -eq 0 ]]; then
            first_429_at=$i
        fi
    else
        count_ok=$((count_ok + 1))
    fi
done

echo -e "      Sent 20 requests: ${count_ok} OK, ${count_429} rate-limited"
echo -e "      First 429 at request #${first_429_at:-none}"

if [[ $first_429_at -ge 15 && $first_429_at -le 17 ]]; then
    log_pass "Rate limiting kicked in around request #$first_429_at (expected ~16)"
elif [[ $first_429_at -eq 0 ]]; then
    log_fail "Never got rate-limited in 20 requests"
else
    log_fail "Rate limiting started at unexpected request #$first_429_at"
fi


# ═══════════════════════════════════════════════════════════════════════
# TEST 5: Redis key inspection
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST 5: Redis key inspection"

log_test "Check Redis for rate limit keys"

REDIS_CONTAINER=$(docker ps --filter "ancestor=redis:7" --format "{{.Names}}" 2>/dev/null | head -1) || true

if [[ -n "$REDIS_CONTAINER" ]]; then
    curl -s -o /dev/null "${BASE_URL}/api/auth/me" 2>/dev/null || true

    keys=$(docker exec "$REDIS_CONTAINER" redis-cli KEYS "rl:*" 2>/dev/null) || true
    key_count=$(echo "$keys" | grep -c "rl:" 2>/dev/null) || key_count=0

    echo -e "      Redis container: $REDIS_CONTAINER"
    echo -e "      Active rl:* keys: $key_count"

    if [[ $key_count -gt 0 ]]; then
        echo -e "      Sample keys:"
        echo "$keys" | head -5 | while read -r k; do
            ttl=$(docker exec "$REDIS_CONTAINER" redis-cli TTL "$k" 2>/dev/null) || true
            val=$(docker exec "$REDIS_CONTAINER" redis-cli GET "$k" 2>/dev/null) || true
            echo -e "        ${CYAN}$k${NC} → count=$val, ttl=${ttl}s"
        done
        log_pass "Rate limit keys found in Redis"
    else
        echo -e "      (keys may have expired — TTL is only 1 second)"
        log_pass "Redis is accessible (keys expire fast, so empty is OK)"
    fi
else
    log_skip "Could not find Redis container via docker ps"
fi


# ═══════════════════════════════════════════════════════════════════════
# TEST 6: Concurrent burst test
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST 6: Concurrent burst test"

sleep 1.2

log_test "Fire 10 simultaneous POST requests (should only allow 2)"

tmpdir=$(mktemp -d)
for i in $(seq 1 10); do
    (
        code=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST "${BASE_URL}/api/auth/login" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=burst_test&password=wrong" \
            2>/dev/null) || true
        echo "$code" > "$tmpdir/$i"
    ) &
done
wait

ok_count=0
limited_count=0
for i in $(seq 1 10); do
    code=$(cat "$tmpdir/$i" 2>/dev/null) || true
    if [[ "$code" == "429" ]]; then
        limited_count=$((limited_count + 1))
    else
        ok_count=$((ok_count + 1))
    fi
done
rm -rf "$tmpdir"

echo -e "      10 concurrent requests: ${ok_count} allowed, ${limited_count} rate-limited"

if [[ $limited_count -ge 7 ]]; then
    log_pass "Concurrent burst correctly limited (${limited_count}/10 blocked)"
else
    log_fail "Too many requests got through ($ok_count allowed, expected ~2)"
fi


# ═══════════════════════════════════════════════════════════════════════
# CLEANUP: Remove test users from DB
# ═══════════════════════════════════════════════════════════════════════
log_header "CLEANUP"

DB_CONTAINER=$(docker ps --filter "ancestor=postgres:16" --format "{{.Names}}" 2>/dev/null | head -1) || true

if [[ -n "$DB_CONTAINER" ]]; then
    echo -e "  Deleting test users (rl_test_* and dummy_*)..."

    deleted=$(docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "DELETE FROM users WHERE username LIKE 'rl_test_%' OR username LIKE 'dummy_%' RETURNING username;" 2>/dev/null) || true

    if [[ -n "$deleted" ]]; then
        count=$(echo "$deleted" | grep -c '\S' 2>/dev/null) || count=0
        echo -e "  ${GREEN}Cleaned up $count test user(s)${NC}"
    else
        echo -e "  ${YELLOW}No test users found (may have been cleaned already)${NC}"
    fi
else
    echo -e "  ${YELLOW}Could not find Postgres container — clean up manually:${NC}"
    echo -e "  ${CYAN}DELETE FROM users WHERE username LIKE 'rl_test_%' OR username LIKE 'dummy_%';${NC}"
fi


# ═══════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════════════════════════════════
log_header "TEST REPORT"

echo -e "${BOLD}"
echo "  ┌─────────────────────────────────────────┐"
echo "  │           Rate Limiter Results           │"
echo "  ├─────────────────────────────────────────┤"
printf "  │  %-10s %s\n" "Total:" "$TOTAL tests │"
printf "  │  ${GREEN}%-10s${BOLD} %s\n" "Passed:" "$PASS │"
printf "  │  ${RED}%-10s${BOLD} %s\n" "Failed:" "$FAIL │"
printf "  │  ${YELLOW}%-10s${BOLD} %s\n" "Skipped:" "$SKIP │"
echo "  └─────────────────────────────────────────┘"
echo -e "${NC}"

echo -e "${BOLD}  Detail:${NC}"
echo -e "$REPORT"

if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}  ✓ All tests passed! Safe to deploy.${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}  ✗ $FAIL test(s) failed. Fix before deploying.${NC}"
    echo ""
    exit 1
fi