import base64
import logging
import os

from manager import BaseManager, helm, kubectl, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.config = self.kwargs.get("config")

    def delete(self):
        """
        Delete the redis addon.
        """
        self.redis(action="delete")

    def install(self):
        """
        Logic for the installation of redis.
        """
        self.redis(action="install")

    def upgrade(self):
        """
        Upgrade the chart installs.
        """
        self.redis(action="upgrade")

    def redis(self, action="upgrade"):
        """
        Handle the values file.
        """
        values = {
            "env": {},
            "resources": {},
            "replica": {
                "replicaCount": 3
            }
        }

        if self.kwargs.get("provider") == "gcp":
            values["nodeSelector"] = {"nodegroup": "addons"}

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "redis",
            "release": f"redis",
        }
        if action != "delete":
            params["chart"] = "bitnami/redis"
            params["values"] = "values.yaml"
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

