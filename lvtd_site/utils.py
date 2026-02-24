import structlog


def get_lvtd_site_logger(name):
    """This will add a `lvtd_site` prefix to logger for easy configuration."""

    return structlog.get_logger(
        f"lvtd_site.{name}",
        project="lvtd_site"
    )
