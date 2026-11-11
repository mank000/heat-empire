#!/bin/bash
set -euo pipefail

site=/opt/heat-empire/12907cd
state=/opt/heat-empire/ci
repo=https://github.com/mank000/heat-empire.git
umask 077
exec 9>"$state/deploy.lock"
flock -n 9

IFS= read -r release
[[ "$release" =~ ^[0-9a-f]{40}$ ]]

main_commit() {
    timeout 25 git ls-remote --exit-code "$repo" refs/heads/main | cut -f1
}
if [[ "$release" != "$(main_commit)" ]]; then
    echo "Refusing a release that is no longer at the tip of main." >&2
    exit 1
fi

cd "$site"
export HEAT_RELEASE_IMAGE="heat-empire-ci:$release"
compose=(docker compose -p heat-empire -f compose.yaml -f compose.preview.yaml -f compose.ci.yaml --profile bot)
previous=$(docker inspect --format '{{.Image}}' heat-empire-web-1)

# Import a filesystem into the one release tag chosen by this script.
# The upload cannot choose Docker tags or change the host's Compose configuration.
timeout 300 docker image import --platform linux/amd64 \
    --change 'WORKDIR /app' \
    --change 'USER 10001:10001' \
    --change 'ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SERVE_STATIC=1 DJANGO_DB_PATH=/data/db.sqlite3' \
    --change 'ENTRYPOINT ["/usr/local/bin/heat-entrypoint"]' \
    --change "LABEL org.opencontainers.image.revision=$release" \
    - "$HEAT_RELEASE_IMAGE"
[[ "$release" == "$(main_commit)" ]]

docker tag "$previous" heat-empire-ci:rollback
backup=$(mktemp "$state/backups/backup-XXXXXX")
"${compose[@]}" exec -T web python /app/backup.py < /dev/null > "$backup"
mv "$backup" "$backup.sqlite3"

site_is_healthy() {
    curl -fsS --max-time 10 --connect-to 89.111.171.123:443:127.0.0.1:443 \
        -o /dev/null https://89.111.171.123/ || return 1
    [[ "$(docker inspect -f '{{.State.Running}}' heat-empire-bot-1)" == true ]]
}

if "${compose[@]}" up --no-build --pull never -d --wait --wait-timeout 60 < /dev/null && site_is_healthy; then
    printf '%s\n' "$release" > "$state/current-sha"
    find "$state/backups" -maxdepth 1 -type f -name 'backup-*.sqlite3' -mtime +14 -delete
    while IFS= read -r tag; do
        if [[ "$tag" != "$release" && "$tag" != rollback ]]; then
            docker image rm "heat-empire-ci:$tag" >/dev/null || true
        fi
    done < <(docker image ls 'heat-empire-ci:*' --format '{{.Tag}}')
    echo "Deployed $release."
else
    export HEAT_RELEASE_IMAGE=heat-empire-ci:rollback
    "${compose[@]}" up --no-build --pull never -d --wait --wait-timeout 60 < /dev/null
    site_is_healthy
    echo "New release failed. Previous image restored. SQLite backup: $backup.sqlite3" >&2
    exit 1
fi
