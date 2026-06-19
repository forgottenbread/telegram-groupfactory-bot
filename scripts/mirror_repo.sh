#!/usr/bin/env bash
set -euo pipefail

DEFAULT_SOURCE_URL="https://git.mulas.me/corrado/telegram-groupfactory-bot.git"
DEFAULT_DESTINATION_URL="https://git.devops.lnxc.it/dev/IMS/telegram-groupfactory-bot.git"

SOURCE_URL="${SOURCE_URL:-$DEFAULT_SOURCE_URL}"
DESTINATION_URL="${DESTINATION_URL:-$DEFAULT_DESTINATION_URL}"
SOURCE_BRANCH="${SOURCE_BRANCH:-master}"
TARGET_BRANCH="${TARGET_BRANCH:-master}"
MR_BRANCH="${MR_BRANCH:-feat}"
MR_TITLE="${MR_TITLE:-Mirror telegram-groupfactory-bot}"
MR_DESCRIPTION="${MR_DESCRIPTION:-Mirror from ${SOURCE_URL} into ${DESTINATION_URL}.}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-Mirror source repository tree}"
WORKDIR=""
KEEP_WORKDIR=0
ASSUME_YES=0
FORCE_WITH_LEASE=1

usage() {
  cat <<'EOF'
Mirror telegram-groupfactory-bot through a GitLab merge request.

Usage:
  scripts/mirror_repo.sh [options]

Options:
  -s, --source URL          Source repository URL.
  -d, --destination URL     Destination repository URL.
      --source-branch NAME  Source branch to copy. Default: master.
      --target-branch NAME  MR target branch. Default: master.
      --mr-branch NAME      Destination feature branch. Default: feat.
      --title TEXT          Merge request title.
      --description TEXT    Merge request description.
      --commit-message TEXT Commit message for the source tree update.
      --no-force-with-lease Use plain --force instead of --force-with-lease.
  -w, --workdir DIR         Directory used for the temporary clone.
  -k, --keep-workdir        Keep the temporary clone after finishing.
  -y, --yes                 Skip the confirmation prompt.
  -h, --help                Show this help.

Environment overrides:
  SOURCE_URL, DESTINATION_URL, SOURCE_BRANCH, TARGET_BRANCH, MR_BRANCH,
  MR_TITLE, MR_DESCRIPTION, COMMIT_MESSAGE
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--source)
      SOURCE_URL="$2"
      shift 2
      ;;
    -d|--destination)
      DESTINATION_URL="$2"
      shift 2
      ;;
    --source-branch)
      SOURCE_BRANCH="$2"
      shift 2
      ;;
    --target-branch)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    --mr-branch)
      MR_BRANCH="$2"
      shift 2
      ;;
    --title)
      MR_TITLE="$2"
      shift 2
      ;;
    --description)
      MR_DESCRIPTION="$2"
      shift 2
      ;;
    --commit-message)
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    --no-force-with-lease)
      FORCE_WITH_LEASE=0
      shift
      ;;
    -w|--workdir)
      WORKDIR="$2"
      shift 2
      ;;
    -k|--keep-workdir)
      KEEP_WORKDIR=1
      shift
      ;;
    -y|--yes)
      ASSUME_YES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$WORKDIR" ]]; then
  WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/telegram-groupfactory-bot-mr.XXXXXX")"
else
  mkdir -p "$WORKDIR"
fi

cleanup() {
  if [[ "$KEEP_WORKDIR" -eq 0 && -n "$WORKDIR" && -d "$WORKDIR" ]]; then
    rm -rf "$WORKDIR"
  fi
}
trap cleanup EXIT

echo "Source:       $SOURCE_URL"
echo "Destination:  $DESTINATION_URL"
echo "Source ref:   $SOURCE_BRANCH"
echo "MR branch:    $MR_BRANCH"
echo "MR target:    $TARGET_BRANCH"
echo "Workdir:      $WORKDIR"
echo

if [[ "$ASSUME_YES" -eq 0 ]]; then
  read -r -p "Create ${MR_BRANCH} from destination/${TARGET_BRANCH}, apply source/${SOURCE_BRANCH}, and create MR? [y/N] " reply
  case "$reply" in
    y|Y|yes|YES)
      ;;
    *)
      echo "Aborted."
      exit 1
      ;;
  esac
fi

echo "Cloning destination target branch..."
git clone --single-branch --branch "$TARGET_BRANCH" "$DESTINATION_URL" "$WORKDIR/repo"

cd "$WORKDIR/repo"
git remote add source "$SOURCE_URL"

echo "Fetching source branch..."
git fetch source "refs/heads/${SOURCE_BRANCH}:refs/remotes/source/${SOURCE_BRANCH}"

echo "Fetching destination MR branch for lease..."
if git fetch origin "refs/heads/${MR_BRANCH}:refs/remotes/origin/${MR_BRANCH}"; then
  MR_REMOTE_COMMIT="$(git rev-parse "refs/remotes/origin/${MR_BRANCH}")"
else
  MR_REMOTE_COMMIT=""
fi

SOURCE_REF="refs/remotes/source/${SOURCE_BRANCH}"
TARGET_REF="refs/remotes/origin/${TARGET_BRANCH}"
SOURCE_COMMIT="$(git rev-parse "$SOURCE_REF")"
TARGET_COMMIT="$(git rev-parse "$TARGET_REF")"

echo "Creating MR branch from destination target..."
git checkout -B "$MR_BRANCH" "$TARGET_REF"

echo "Applying source tree from ${SOURCE_COMMIT}..."
git read-tree --reset -u "$SOURCE_REF"

if git diff --cached --quiet; then
  echo "Destination ${TARGET_BRANCH} already has the same tree as source ${SOURCE_BRANCH}."
  echo "Nothing to push."
  exit 0
fi

git commit \
  -m "$COMMIT_MESSAGE" \
  -m "Source: $SOURCE_URL" \
  -m "Source branch: $SOURCE_BRANCH" \
  -m "Source commit: $SOURCE_COMMIT" \
  -m "Destination base: $DESTINATION_URL" \
  -m "Destination target: $TARGET_BRANCH" \
  -m "Destination base commit: $TARGET_COMMIT"

push_args=()
if [[ "$FORCE_WITH_LEASE" -eq 1 ]]; then
  push_args+=(--force-with-lease="refs/heads/${MR_BRANCH}:${MR_REMOTE_COMMIT}")
else
  push_args+=(--force)
fi

echo "Pushing MR branch and asking GitLab to create the merge request..."
git push "${push_args[@]}" \
  -o merge_request.create \
  -o merge_request.target="$TARGET_BRANCH" \
  -o merge_request.title="$MR_TITLE" \
  -o merge_request.description="$MR_DESCRIPTION" \
  origin "HEAD:refs/heads/${MR_BRANCH}"

echo "Merge request push complete."
