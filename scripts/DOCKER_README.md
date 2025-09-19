# Using Docker
Build the image and run the container (in the project root):

```bash
# build
docker-compose build
# run in background
docker-compose up -d
# see logs
docker-compose logs -f autodubber
```

Mounts/volumes used:
- `./config.json` (read-only) - your filled configuration
- `./client_secrets.json` (read-only) - YouTube OAuth client secrets for initial auth
- `./drive_service_account.json` (read-only, optional) - Drive service account key if you use Drive features
- `./tmp` - persistent tmp directory (optional)

Note: the container installs a CPU version of PyTorch by default. If you have GPU support, modify the Dockerfile accordingly.