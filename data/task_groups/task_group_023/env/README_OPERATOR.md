# Public Health Observatory environment

This directory is the complete build context for the read-only portal. The data generator uses fixed seed `23072026`; rebuilding or reseeding produces the same logical records and manifests.

## Build and isolated run

```sh
docker build -t task-group-023-env:latest .
docker network create observatory-check
docker run -d --rm --name observatory-env --network observatory-check \
  --network-alias task-env -e TASK_ENV_BIND=0.0.0.0 -e TASK_ENV_PORT=9023 \
  task-group-023-env:latest
docker run --rm --network observatory-check curlimages/curl:latest \
  -fsS http://task-env:9023/health
```

Do not publish a host port. Solver containers should join the owner/run-scoped user-defined bridge and use `http://task-env:9023/`.

Judge mode is disabled unless the container receives `TASK_ENV_ENABLE_JUDGE=1`. When enabled, `train_001` through `train_005` run their matching self-contained evaluator-equivalent copy in a bounded subprocess. The environment packages no separate standard-answer files, and the evaluator copies contain only analytical expectations required by their rubrics. Only the normalized score, correctness flag, and fixed train-only notice leave the service. Test and unknown IDs receive a non-diagnostic rejection; request size and evaluator runtime are limited.

```sh
docker run -d --rm --name observatory-train --network observatory-check \
  --network-alias task-env -e TASK_ENV_ENABLE_JUDGE=1 task-group-023-env:latest
```

The image also supports operator checks without starting the server:

```sh
docker run --rm task-group-023-env:latest --check
docker run --rm task-group-023-env:latest --reseed
```

`--reseed` generates a temporary database, validates it, and atomically replaces `generated/observatory.sqlite`. The associated manifests are replaced at the same time. A mounted writable location may be selected with `TASK_ENV_DB_PATH`.

Stop the portal and remove the bridge after use:

```sh
docker rm -f observatory-env observatory-train
docker network rm observatory-check
```
