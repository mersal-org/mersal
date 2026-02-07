import subprocess

__all__ = ("is_docker_available",)


def is_docker_available() -> bool:
    try:
        _ = subprocess.check_output(["/usr/bin/docker", "info"], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
