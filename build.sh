#!/bin/sh
# Build a tagged postfix image, e.g. ./build.sh 0.6.2, then set
# POSTFIX_IMAGE=postfix:0.6.2 in .env and run `docker compose up -d`.
set -e
tag=${1:?usage: $0 <version>}
cd "$(dirname "$0")"
docker build --tag="postfix:$tag" .
