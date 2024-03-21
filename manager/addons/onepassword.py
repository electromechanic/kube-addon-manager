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
        Delete the onepassword addon.
        """
        self.onepassword(action="delete")
        self.secrets_injector(action="delete")
        kubectl(action="delete mutatingwebhookconfigurations secrets-injector-webhook-config")

    def install(self):
        """
        Logic for the installation of onepassword.
        """
        self.onepassword(action="upgrade")
        self.secrets_injector(action="upgrade")

    def onepassword(self, action="upgrade"):
        """
        Install onepassword
        """
        with open(self.config.credentials_file, "r") as f:
            creds = f.read()

        values = {
            "connect": {
                "credentials": creds
                },
            "operator": {
                "create": True,
                "token": {
                    "value":  os.getenv("OP_CONNECT_TOKEN")
                    }
                }
        }

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "onepassword",
            "release": "onepassword-connect",
        }
        if action != "delete":
            params["chart"] = "onepassword/connect"
            params["values"] = "values.yaml"
            params["version"] = self.config.connect_version
            logger.info("Values for helm chart are:\n%s",
                        utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def secrets_injector(self, action="upgrade"):
        """
        Install onepassword secrets injector
        """
        values = {
            "injector": {
                "version": self.config.secrets_injector_version
            }
        }
        params = {
            "action": action,
            "namespace": "onepassword",
            "release": "secrets-injector",
        }

        if action != "delete":
            params["chart"] = "onepassword/secrets-injector"
            params["version"] = self.config.secrets_injector_chart_version
            logger.info("Using default values for helm chart")

        helm(**params)

    def upgrade(self):
        """
        Upgrade the chart installs.
        """
        self.onepassword(action="upgrade")
        self.secrets_injector(action="upgrade")
