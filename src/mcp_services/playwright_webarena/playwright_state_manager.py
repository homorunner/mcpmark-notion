"""
WebArena (Docker) State Manager for MCPBench
===========================================

This module manages a WebArena environment that runs inside a Docker container.
It is responsible for starting the container in the initial state phase and
stopping/removing it during cleanup. It exposes the target URL (e.g.
http://localhost:9999) for Playwright MCP-based automation.
"""

from __future__ import annotations

import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DockerConfig:
    image_name: str = "postmill-populated-exposed-withimg"
    image_tar_path: Optional[Path] = None
    container_name: str = "forum"
    host_port: int = 9999
    container_port: int = 80
    readiness_path: str = "/"
    readiness_timeout_seconds: int = 600
    readiness_poll_interval_seconds: float = 2.0

    @property
    def base_url(self) -> str:
        return f"http://35.247.158.69:{self.host_port}"


class PlaywrightStateManager(BaseStateManager):
    """
    Manage Docker lifecycle for WebArena-backed tasks.

    - Initial state: ensure image is present (optionally load from tar), then
      run container and wait until HTTP endpoint is ready.
    - Cleanup: stop and remove the container.
    """

    def __init__(
        self,
        *,
        docker_image_name: str = "postmill-populated-exposed-withimg",
        docker_container_name: str = "forum",
        host_port: int = 9999,
        container_port: int = 80,
        image_tar_path: Optional[str | Path] = None,
        readiness_path: str = "/",
        readiness_timeout_seconds: int = 600,
        readiness_poll_interval_seconds: float = 2.0,
        # Playwright browser config params (ignored by this state manager)
        browser: Optional[str] = None,
        headless: Optional[bool] = None,
        network_origins: Optional[str] = None,
        user_profile: Optional[str] = None,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
        # Debug mode - skip container cleanup
        skip_cleanup: bool = False,
    ) -> None:
        super().__init__(service_name="playwright_webarena")

        self.config = DockerConfig(
            image_name=docker_image_name,
            image_tar_path=Path(image_tar_path).expanduser().resolve() if image_tar_path else None,
            container_name=docker_container_name,
            host_port=host_port,
            container_port=container_port,
            readiness_path=readiness_path,
            readiness_timeout_seconds=readiness_timeout_seconds,
            readiness_poll_interval_seconds=readiness_poll_interval_seconds,
        )
        
        self.skip_cleanup = skip_cleanup

        logger.info(
            "Initialized WebArenaStateManager (image=%s, container=%s, port=%s, skip_cleanup=%s)",
            self.config.image_name,
            self.config.container_name,
            self.config.host_port,
            self.skip_cleanup,
        )

    # ---- Helpers ---------------------------------------------------------

    def _run_cmd(self, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
        logger.debug("Running command: %s", " ".join(args))
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=check)

    def _image_exists(self, image: str) -> bool:
        result = self._run_cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"])
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        # Parse target image (allow optional tag; default latest)
        if ":" in image:
            target_repo, target_tag = image.split(":", 1)
        else:
            target_repo, target_tag = image, "latest"

        for repo_tag in lines:
            if ":" in repo_tag:
                repo, tag = repo_tag.split(":", 1)
            else:
                repo, tag = repo_tag, "latest"
            if repo == target_repo and tag == target_tag:
                logger.debug("Found Docker image %s:%s", repo, tag)
                return True
        logger.debug("Docker image not found: %s:%s", target_repo, target_tag)
        return False

    def _load_image_from_tar_if_needed(self) -> None:
        if self.config.image_tar_path and not self._image_exists(self.config.image_name):
            logger.info("Loading Docker image from tar: %s", self.config.image_tar_path)
            result = self._run_cmd(["docker", "load", "--input", str(self.config.image_tar_path)])
            if result.returncode != 0:
                logger.error("Failed to load Docker image: %s", result.stderr.strip())
                raise RuntimeError(f"docker load failed: {result.stderr}")
            logger.info("Docker image loaded")

    def _stop_and_remove_container(self, name: str) -> None:
        # Stop (ignore errors if not running)
        self._run_cmd(["docker", "stop", name])
        # Remove (ignore errors if not exists)
        self._run_cmd(["docker", "rm", name])

    def _container_is_running(self, name: str) -> bool:
        result = self._run_cmd(["docker", "ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"])
        running = any(line.strip() == name for line in result.stdout.splitlines())
        logger.debug("Container '%s' running: %s", name, running)
        return running

    def _port_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False

    def _http_ready(self, url: str) -> bool:
        try:
            resp = requests.get(url, timeout=3)
            return resp.status_code < 500
        except Exception:
            return False

    def _wait_until_ready(self) -> bool:
        deadline = time.time() + self.config.readiness_timeout_seconds
        base_url = self.config.base_url.rstrip("/")
        url = f"{base_url}{self.config.readiness_path}"

        # First wait for port to open to avoid long HTTP errors
        while time.time() < deadline:
            if self._port_open("35.247.158.69", self.config.host_port):
                break
            time.sleep(self.config.readiness_poll_interval_seconds)

        while time.time() < deadline:
            if self._http_ready(url):
                logger.info("WebArena HTTP endpoint ready: %s", url)
                return True
            time.sleep(self.config.readiness_poll_interval_seconds)

        logger.error("Timed out waiting for WebArena at %s", url)
        return False

    # ---- BaseStateManager hooks -----------------------------------------

    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        try:
            # Ensure image exists (load from tar if configured)
            self._load_image_from_tar_if_needed()

            # Ensure any stale container is gone
            self._stop_and_remove_container(self.config.container_name)

            # Run container
            run_cmd = [
                "docker",
                "run",
                "--name",
                self.config.container_name,
                "-p",
                f"{self.config.host_port}:{self.config.container_port}",
                "-d",
                self.config.image_name,
            ]
            result = self._run_cmd(run_cmd)
            if result.returncode != 0:
                logger.error("Failed to start container: %s", result.stderr.strip())
                return None
            container_id = result.stdout.strip()
            logger.info("Started container %s (%s)", self.config.container_name, container_id)

            # Wait for readiness
            if not self._wait_until_ready():
                # Cleanup on failure
                self._stop_and_remove_container(self.config.container_name)
                return None

            # Track resource for cleanup
            self.track_resource(
                "docker_container",
                self.config.container_name,
                {
                    "image": self.config.image_name,
                    "host_port": self.config.host_port,
                    "container_port": self.config.container_port,
                    "base_url": self.config.base_url,
                },
            )

            # Provide initial state info
            return InitialStateInfo(
                state_id=self.config.container_name,
                state_url=self.config.base_url,
                metadata={
                    "docker_image": self.config.image_name,
                    "container_name": self.config.container_name,
                    "host_port": self.config.host_port,
                    "container_port": self.config.container_port,
                    "base_url": self.config.base_url,
                    "category": task.category,
                },
            )
        except Exception as exc:
            logger.error("Failed to create WebArena initial state: %s", exc)
            return None

    def _store_initial_state_info(self, task: BaseTask, state_info: InitialStateInfo) -> None:
        if hasattr(task, "__dict__"):
            task.docker_container_name = state_info.state_id
            task.base_url = state_info.state_url
            task.docker_metadata = state_info.metadata

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        if self.skip_cleanup:
            logger.info("Skipping container cleanup (skip_cleanup=True)")
            logger.info("Container is still running at: %s", self.config.base_url)
            logger.info("To manually stop: docker stop %s && docker rm %s", 
                       self.config.container_name, self.config.container_name)
            return True
            
        try:
            self._stop_and_remove_container(self.config.container_name)
            return True
        except Exception as exc:
            logger.error("Failed to cleanup container for %s: %s", task.name, exc)
            return False

    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        if self.skip_cleanup:
            logger.info("Skipping resource cleanup for %s (skip_cleanup=True)", resource.get("id"))
            return True
            
        try:
            if resource.get("type") == "docker_container":
                self._stop_and_remove_container(resource["id"])
                return True
            logger.warning("Unknown resource type for cleanup: %s", resource.get("type"))
            return False
        except Exception as exc:
            logger.error("Resource cleanup failed: %s", exc)
            return False

    def get_service_config_for_agent(self) -> dict:
        """
        Provide configuration to the agent. The key piece is the base URL that
        agents should navigate to when starting tasks.
        """
        return {
            "environment": "webarena-docker",
            "base_url": self.config.base_url,
            "docker": {
                "image": self.config.image_name,
                "container": self.config.container_name,
                "host_port": self.config.host_port,
                "container_port": self.config.container_port,
            },
        }

    def close_all(self) -> None:
        if self.skip_cleanup:
            logger.info("Skipping container cleanup in close_all (skip_cleanup=True)")
            return
            
        try:
            self._stop_and_remove_container(self.config.container_name)
        except Exception:
            # Best effort
            pass

    def __del__(self) -> None:
        if not self.skip_cleanup:
            self.close_all() 