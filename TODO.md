# TODO

## Home Assistant Add-on Development

### Phase 1: Core Add-on Structure

- [ ] Update `aquable/build.yaml` - Configure amd64 base image only for development
  - Use `ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.21`
  - Remove multi-arch configurations for now
  
- [ ] Update `aquable/config.yaml` - Enhance with Bashio-friendly schema
  - Add `bluetooth: true` for BLE access
  - Add `hassio_api: true` for Supervisor API
  - Add `homeassistant_api: true` for timezone access
  - Configure timezone options with "auto" default
  
- [ ] Update `aquable/Dockerfile` - Optimize for HA base image
  - Use `${BUILD_FROM}` with HA Python base
  - Leverage pre-configured S6-overlay
  - Multi-stage build with frontend compilation
  
- [ ] Update `aquable/rootfs/etc/services.d/aquable/run` - Implement Bashio configuration
  - Read add-on options via `bashio::config`
  - Handle timezone auto-detection from HA API
  - Export `AQUA_BLE_*` environment variables
  - Set proper paths for add-on environment

### Phase 2: Build Automation

- [ ] Create `.github/workflows/build-push.yaml` - Automated add-on builds
  - Trigger on version tags and manual workflow dispatch
  - Build frontend assets
  - Use `home-assistant/builder@master` action
  - Push to GitHub Container Registry (ghcr.io)

### Phase 3: Documentation & Testing

- [ ] Enhance `aquable/DOCS.md` - Add data persistence documentation
  - Document `/data` mapping to HA persistent storage
  - Explain storage structure (`global_settings.json`, `devices/`)
  - Note survival across restarts/updates/reboots
  
- [ ] Create `scripts/test_addon_local.sh` - Local testing workflow
  - Build add-on with existing `build_addon_local.sh`
  - Optional HA CLI integration testing
  - Log verification steps

## Reference Links

### Python Base Images

- <https://github.com/home-assistant/docker-base/tree/master>

### Add-on Structure Example

- <https://github.com/home-assistant/addons-example>
