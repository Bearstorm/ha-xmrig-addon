
#!/usr/bin/env bash
set -euo pipefail

# ==================================================
# XMRig 2.0 - Release Policy Tests
#
# Tests the shared release policy script.
#
# No real Git tags are created.
# No Docker images are built or published.
# No network connections are required.
# ==================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY_SCRIPT="${ROOT_DIR}/scripts/release_policy.sh"

PASS=0
FAIL=0

TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT

OUTPUT_FILE="${TEST_DIR}/output.log"
RESULT_FILE="${TEST_DIR}/github-output.txt"

MAIN_SHA="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OTHER_SHA="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

# --------------------------------------------------
# 1. Prerequisites
# --------------------------------------------------

command -v bash >/dev/null 2>&1 || {
    echo "ERROR: Bash is missing"
    exit 1
}

if [[ ! -f "$POLICY_SCRIPT" ]]; then
    echo "ERROR: Shared release policy not found:"
    echo "$POLICY_SCRIPT"
    exit 1
fi

bash -n "$POLICY_SCRIPT"

# --------------------------------------------------
# 2. Test helpers
# --------------------------------------------------

run_policy() {
    local event_name="$1"
    local git_ref="$2"
    local ref_name="$3"
    local release_sha="$4"
    local main_sha="$5"

    : > "$RESULT_FILE"

    EVENT_NAME="$event_name" \
    GIT_REF="$git_ref" \
    REF_NAME="$ref_name" \
    RELEASE_SHA="$release_sha" \
    MAIN_SHA="$main_sha" \
    GITHUB_OUTPUT="$RESULT_FILE" \
        bash "$POLICY_SCRIPT" > "$OUTPUT_FILE" 2>&1
}

assert_output_value() {
    local key="$1"
    local value="$2"

    grep -Fxq "${key}=${value}" "$RESULT_FILE"
}

pass() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}

fail() {
    FAIL=$((FAIL + 1))

    echo "FAIL: $1"
    echo "--- Policy log ---"
    cat "$OUTPUT_FILE" || true
    echo "--- Policy output ---"
    cat "$RESULT_FILE" || true
    echo "-------------------"
}

expect_allowed() {
    local title="$1"
    local event="$2"
    local ref="$3"
    local name="$4"
    local sha="$5"
    local expected_tag="$6"

    if run_policy \
        "$event" "$ref" "$name" "$sha" "$MAIN_SHA" &&
       assert_output_value "push_image" "true" &&
       assert_output_value "image_tag" "$expected_tag"; then

        pass "$title"
    else
        fail "$title"
    fi
}

expect_build_only() {
    local title="$1"
    local event="$2"
    local ref="$3"
    local name="$4"
    local sha="$5"

    if run_policy \
        "$event" "$ref" "$name" "$sha" "$MAIN_SHA" &&
       assert_output_value "push_image" "false" &&
       assert_output_value "image_tag" "development"; then

        pass "$title"
    else
        fail "$title"
    fi
}

expect_rejected() {
    local title="$1"
    local event="$2"
    local ref="$3"
    local name="$4"
    local sha="$5"

    if run_policy \
        "$event" "$ref" "$name" "$sha" "$MAIN_SHA"; then

        fail "$title"
    else
        if ! assert_output_value "push_image" "true"; then
            pass "$title"
        else
            fail "$title"
        fi
    fi
}

# --------------------------------------------------
# 3. Run tests
# --------------------------------------------------

echo "======================================"
echo "XMRig 2.0 - Release Policy Tests"
echo "======================================"

# TEST 01 - Development branch
expect_build_only \
    "Development branch cannot publish" \
    "push" \
    "refs/heads/develop-v2" \
    "develop-v2" \
    "$OTHER_SHA"

# TEST 02 - Pull request
expect_build_only \
    "Pull request cannot publish" \
    "pull_request" \
    "refs/pull/3/merge" \
    "3/merge" \
    "$OTHER_SHA"

# TEST 03 - Manual workflow
expect_build_only \
    "Manual workflow cannot publish" \
    "workflow_dispatch" \
    "refs/heads/main" \
    "main" \
    "$MAIN_SHA"

# TEST 04 - Main branch
expect_allowed \
    "Main branch publishes latest" \
    "push" \
    "refs/heads/main" \
    "main" \
    "$MAIN_SHA" \
    "latest"

# TEST 05 - Stable release
expect_allowed \
    "Stable v2.0.0 release" \
    "push" \
    "refs/tags/v2.0.0" \
    "v2.0.0" \
    "$MAIN_SHA" \
    "v2.0.0"

# TEST 06 - Beta release
expect_allowed \
    "Beta v2.0.0-beta.1 release" \
    "push" \
    "refs/tags/v2.0.0-beta.1" \
    "v2.0.0-beta.1" \
    "$MAIN_SHA" \
    "v2.0.0-beta.1"

# TEST 07 - Another stable version
expect_allowed \
    "Stable v2.1.3 release" \
    "push" \
    "refs/tags/v2.1.3" \
    "v2.1.3" \
    "$MAIN_SHA" \
    "v2.1.3"

# TEST 08 - Commit outside main
expect_rejected \
    "Release outside main is rejected" \
    "push" \
    "refs/tags/v2.0.0" \
    "v2.0.0" \
    "$OTHER_SHA"

# TEST 09 - Invalid version format
expect_rejected \
    "Incomplete release version rejected" \
    "push" \
    "refs/tags/v2.0" \
    "v2.0" \
    "$MAIN_SHA"

# TEST 10 - Unsupported prerelease
expect_rejected \
    "Unsupported prerelease rejected" \
    "push" \
    "refs/tags/v2.0.0-rc.1" \
    "v2.0.0-rc.1" \
    "$MAIN_SHA"

# TEST 11 - Leading zero
expect_rejected \
    "Leading zero in version rejected" \
    "push" \
    "refs/tags/v2.01.0" \
    "v2.01.0" \
    "$MAIN_SHA"

# TEST 12 - Invalid beta number
expect_rejected \
    "Beta zero rejected" \
    "push" \
    "refs/tags/v2.0.0-beta.0" \
    "v2.0.0-beta.0" \
    "$MAIN_SHA"

# TEST 13 - Another branch
expect_build_only \
    "Other branches cannot publish" \
    "push" \
    "refs/heads/feature-test" \
    "feature-test" \
    "$OTHER_SHA"

# TEST 14 - Main branch PR
expect_build_only \
    "PR targeting main is build-only" \
    "pull_request" \
    "refs/pull/5/merge" \
    "5/merge" \
    "$MAIN_SHA"

# TEST 15 - Tag with extra suffix
expect_rejected \
    "Unexpected release suffix rejected" \
    "push" \
    "refs/tags/v2.0.0-backup" \
    "v2.0.0-backup" \
    "$MAIN_SHA"

# TEST 16 - Empty release SHA
expect_rejected \
    "Missing release commit rejected" \
    "push" \
    "refs/tags/v2.0.0" \
    "v2.0.0" \
    ""

# --------------------------------------------------
# 4. Final summary
# --------------------------------------------------

echo
echo "======================================"
echo "Release Policy Test Results"
echo "======================================"
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo "Total:  $((PASS + FAIL))"
echo "======================================"

if (( FAIL > 0 )); then
    echo "Release policy tests FAILED."
    exit 1
fi

echo "All release policy tests passed."
exit 0
