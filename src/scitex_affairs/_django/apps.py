"""Django registration through the public scitex-app embedding API."""

from scitex_app.embed import ScitexAppConfig


class AffairsAppConfig(ScitexAppConfig):
    name = "scitex_affairs._django"
    label = "scitex_affairs_app"
    verbose_name = "SciTeX Affairs"
