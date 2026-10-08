#!/usr/bin/env bash
set -euo pipefail

# ==================================================
# XMRig 2.0 - Shared Release Policy
#
# Determines whether GHCR image publishing is allowed.
#
# Used by:
#   - GitHub Actions publish.yml
#   - tests/test_release_policy.sh
#
# This script does not:
#   - Create or modify Git tags
#   - Build Docker images
#   - Publish Docker images
#   - Connect to mining pools
#
# GitHub workflow must independently retrieve the
# trusted main branch commit before calling this script.
# ==================================================

# --------------------------------------------------
# 1. Logging and errors
# --------------------------------------------------

log() {
    printf '[release-policy] %s\n' "$*"
}

fail() {
    printf '[release-policy] ERROR: %s\n' "$*" >&2
    exit 1
}

# --------------------------------------------------
# 2. Load GitHub event information
# --------------------------------------------------

EVENT_NAME="${EVENT_NAME:-}"
GIT_REF="${GIT_REF:-}"
REF_NAME="${REF_NAME:-}"
RELEASE_SHA="${RELEASE_SHA:-}"
MAIN_SHA="${MAIN_SHA:-}"
OUTPUT_FILE="${GITHUB_OUTPUT:-}"

[[ -n "$EVENT_NAME" ]] ||
    fail "Missing EVENT_NAME"

[[ -n "$GIT_REF" ]] ||
    fail "Missing GIT_REF"

[[ -n "$OUTPUT_FILE" ]] ||
    fail "Missing GITHUB_OUTPUT"

[[ -f "$OUTPUT_FILE" || -e "$(dirname "$OUTPUT_FILE")" ]] ||
    fail "GitHub output destination is unavailable"

# --------------------------------------------------
# 3. Default policy: build only
# --------------------------------------------------

PUSH_IMAGE=false
IMAGE_TAG=development

log "Event: $EVENT_NAME"
log "Git ref: $GIT_REF"

# --------------------------------------------------
# 4. Evaluate GitHub event
# --------------------------------------------------

case "$EVENT_NAME" in

    pull_request)
        log "Pull request: build only"
        ;;

    workflow_dispatch)
        log "Manual workflow: build only"
        ;;

    push)

        # ------------------------------------------
        # Stable main branch
        # ------------------------------------------

        if [[ "$GIT_REF" == "refs/heads/main" ]]; then

            PUSH_IMAGE=true
            IMAGE_TAG=latest

            log "Main branch publication approved"

        # ------------------------------------------
        # Version 2 release tags
        # ------------------------------------------

        elif [[ "$GIT_REF" == refs/tags/v2.* ]]; then

            [[ -n "$REF_NAME" ]] ||
                fail "Missing release tag name"

            [[ "$GIT_REF" == "refs/tags/$REF_NAME" ]] ||
                fail "Release tag name does not match Git ref"

            # Supported:
            # v2.0.0
            # v2.1.3
            # v2.0.0-beta.1
            #
            # Unsupported:
            # v2.0
            # v2.01.0
            # v2.0.0-beta.0
            # v2.0.0-rc.1

            VERSION_PATTERN='^v2\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-beta\.[1-9][0-9]*)?$'

            if [[ ! "$REF_NAME" =~ $VERSION_PATTERN ]]; then
                fail "Invalid release tag format: $REF_NAME"
            fi

            # Commit SHA values must be provided
            # by the workflow, not by the Git tag name.

            [[ "$RELEASE_SHA" =~ ^[0-9a-fA-F]{40}$ ]] ||
                fail "Missing or invalid release commit SHA"

            [[ "$MAIN_SHA" =~ ^[0-9a-fA-F]{40}$ ]] ||
                fail "Missing or invalid main commit SHA"

            log "Main commit: $MAIN_SHA"
            log "Release commit: $RELEASE_SHA"

            # Only an exact match with the approved
            # main branch HEAD is allowed.

            if [[ "${RELEASE_SHA,,}" != "${MAIN_SHA,,}" ]]; then
                fail "Release tag does not point to current main HEAD"
            fi

            PUSH_IMAGE=true
            IMAGE_TAG="$REF_NAME"

            if [[ "$REF_NAME" == *-beta.* ]]; then
                log "Beta release approved"
            else
                log "Stable release approved"
            fi

        # ------------------------------------------
        # All other branches
        # ------------------------------------------

        else
            log "Development branch: build only"
        fi
        ;;

    *)
        log "Unsupported event: build only"
        ;;

esac

# --------------------------------------------------
# 5. Export policy result
# --------------------------------------------------

{
    printf 'push_image=%s\n' "$PUSH_IMAGE"
    printf 'image_tag=%s\n' "$IMAGE_TAG"
} >> "$OUTPUT_FILE"

log "Publish image: $PUSH_IMAGE"
log "Image tag: $IMAGE_TAG"

# --------------------------------------------------
# 6. Completion
# --------------------------------------------------

log "Release policy validation completed"
exit 0

