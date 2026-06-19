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
COMMIT_MESSAGE="${COMMIT_MESSAGE:-}"
WORKDIR=""
KEEP_WORKDIR=0
ASSUME_YES=0
FORCE_WITH_LEASE=1
SRC_ONLY="${SRC_ONLY:-0}"

usage() {
  cat <<'EOF'
Mirror telegram-groupfactory-bot through a GitLab merge request.

This script:
  1. Clones DESTINATION_URL / TARGET_BRANCH into a temporary workdir.
  2. Fetches SOURCE_URL / SOURCE_BRANCH.
  3. Creates MR_BRANCH from TARGET_BRANCH.
  4. Replaces the MR_BRANCH tree with the source branch tree.
  5. Pushes MR_BRANCH and asks GitLab to create a merge request.

It does not push directly to the protected target branch.
Because the MR branch starts from the destination target branch, it avoids
"source branch is behind target" merge conflicts caused by protected master.

Use --src-only to mirror the source repository while preserving destination
deployment/example folders: argo/, argocd/, examples/, and k8s/.

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
      --src-only            Mirror everything except argo/, argocd/, examples/, and k8s/.
      --no-force-with-lease Use plain --force instead of --force-with-lease.
  -w, --workdir DIR         Directory used for the temporary clone.
  -k, --keep-workdir        Keep the temporary clone after finishing.
  -y, --yes                 Skip the confirmation prompt.
  -h, --help                Show this help.

Environment overrides:
  SOURCE_URL, DESTINATION_URL, SOURCE_BRANCH, TARGET_BRANCH, MR_BRANCH,
  MR_TITLE, MR_DESCRIPTION, COMMIT_MESSAGE, SRC_ONLY

Defaults:
  source:      https://git.mulas.me/corrado/telegram-groupfactory-bot.git
  destination: https://git.devops.lnxc.it/dev/IMS/telegram-groupfactory-bot.git
  source ref:  master
  MR branch:   feat
  MR target:   master
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
    --src-only)
      SRC_ONLY=1
      shift
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

case "$SRC_ONLY" in
  1|true|TRUE|yes|YES)
    SRC_ONLY=1
    ;;
  0|false|FALSE|no|NO|"")
    SRC_ONLY=0
    ;;
  *)
    echo "SRC_ONLY must be 1/0, true/false, or yes/no." >&2
    exit 2
    ;;
esac

if [[ -z "$COMMIT_MESSAGE" ]]; then
  if [[ "$SRC_ONLY" -eq 1 ]]; then
    COMMIT_MESSAGE="Mirror source tree excluding deployment folders"
  else
    COMMIT_MESSAGE="Mirror source repository tree"
  fi
fi

if [[ -z "$SOURCE_URL" || -z "$DESTINATION_URL" ]]; then
  echo "Both source and destination URLs are required." >&2
  exit 2
fi

if [[ -z "$SOURCE_BRANCH" || -z "$TARGET_BRANCH" || -z "$MR_BRANCH" ]]; then
  echo "Source branch, target branch, and MR branch are required." >&2
  exit 2
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required but was not found in PATH." >&2
  exit 1
fi

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
if [[ "$SRC_ONLY" -eq 1 ]]; then
  echo "Mirror mode:  full tree excluding argo/, argocd/, examples/, k8s/"
else
  echo "Mirror mode:  full tree"
fi
echo "Workdir:      $WORKDIR"
echo

if [[ "$ASSUME_YES" -eq 0 ]]; then
  if [[ "$SRC_ONLY" -eq 1 ]]; then
    prompt="Create ${MR_BRANCH} from destination/${TARGET_BRANCH}, apply source/${SOURCE_BRANCH} excluding argo/, argocd/, examples/, k8s/, and create MR? [y/N] "
  else
    prompt="Create ${MR_BRANCH} from destination/${TARGET_BRANCH}, apply source/${SOURCE_BRANCH}, and create MR? [y/N] "
  fi
  read -r -p "$prompt" reply
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

if [[ "$SRC_ONLY" -eq 1 ]]; then
  echo "Applying source tree from ${SOURCE_COMMIT}, preserving deployment/example folders from destination..."
  git read-tree --reset -u "$SOURCE_REF"

  preserved_paths=(argo argocd examples k8s)
  for preserved_path in "${preserved_paths[@]}"; do
    if git cat-file -e "${TARGET_REF}:${preserved_path}" 2>/dev/null; then
      echo "Preserving ${preserved_path}/ from destination ${TARGET_BRANCH}..."
      git checkout "$TARGET_REF" -- "$preserved_path"
    else
      echo "Removing ${preserved_path}/ because it is not present in destination ${TARGET_BRANCH}..."
      git rm -r --ignore-unmatch -- "$preserved_path"
    fi
  done
else
  echo "Applying source tree from ${SOURCE_COMMIT}..."
  git read-tree --reset -u "$SOURCE_REF"
fi

if git diff --cached --quiet; then
  if [[ "$SRC_ONLY" -eq 1 ]]; then
    echo "Destination ${TARGET_BRANCH} already has the same source tree as ${SOURCE_BRANCH}, excluding preserved folders."
  else
    echo "Destination ${TARGET_BRANCH} already has the same tree as source ${SOURCE_BRANCH}."
  fi
  echo "Nothing to push."
  exit 0
fi

git commit \
  -m "$COMMIT_MESSAGE" \
  -m "Source: $SOURCE_URL" \
  -m "Source branch: $SOURCE_BRANCH" \
  -m "Source commit: $SOURCE_COMMIT" \
  -m "Mirror mode: $([[ "$SRC_ONLY" -eq 1 ]] && echo "full tree excluding argo/, argocd/, examples/, k8s/" || echo "full tree")" \
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
