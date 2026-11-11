# Docker Log Sources

Use only for Docker sources, within the services, instances, time window, and keywords fixed by the entrypoint. Common
collection and evidence requirements still apply.

- Resolve Docker services using container names and Compose service/project labels, and fix container identities.
  Preserve instance distinctions for services with multiple instances. Use `docker logs` for live logs and prefer
  container-mounted host log directories for historical logs.
- Live logs: use `docker logs --since/--until --timestamps` on the specified services' containers for a fixed window,
  then match complete events by keywords. Include stdout/stderr and check the logging driver, retention, and rotation
  limits. For continuous observation, use `--follow` with the observation deadline required
  by [Collection and Completeness](SKILL.md#4-collection-and-completeness).
- Historical logs: use `docker inspect` to verify mount destinations and host sources, then locate and read files
  according to [User-Supplied Files or Excerpts](SKILL.md#31-user-supplied-files-or-excerpts). When many mounts exist,
  narrow candidates by service and mount relationships, and locate logs using time range and keywords rather than
  scanning all mounted directories.
- If mounts are missing, an old container has been removed and its original mounts cannot be confirmed, permissions are
  insufficient, or retention is inadequate, report verified coverage and gaps. Do not silently substitute Docker logs
  and claim historical coverage. Supplement with other sources only when their coverage is verified and they fit the
  user's goal.
