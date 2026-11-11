#!/bin/sh
set -eu

cert_root=/opt/heat-empire/acme
webroot=/var/www/heat-empire-acme
fullchain="$cert_root/config/live/heat-empire-ip/fullchain.pem"
previous=$(sha256sum "$fullchain")

docker run --rm --network host \
    -v "$cert_root/config:/etc/letsencrypt" \
    -v "$cert_root/work:/var/lib/letsencrypt" \
    -v "$cert_root/logs:/var/log/letsencrypt" \
    -v "$webroot:$webroot" \
    certbot/certbot:v5.4.0 renew --non-interactive --cert-name heat-empire-ip "$@"

if [ "$(sha256sum "$fullchain")" != "$previous" ]; then
    nginx -t
    systemctl reload nginx
fi
