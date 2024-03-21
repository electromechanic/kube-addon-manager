import base64
import logging
import os

from manager import BaseManager, helm, kubectl, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.args = self.kwargs.get("args")
        self.config = self.kwargs.get("config")

    def delete(self):
        """
        Delete the pgadmin addon.
        """
        self.pgadmin(action="delete")

    def install(self):
        """
        Logic for the installation of sumoligc.
        """
        self.pgadmin_password_secret(action="create")
        self.pgadmin(action="install")

    def pgadmin(self, action="upgrade"):
        """
        Handle the values file.
        """
        values = {
            "env": {"email": "ryan@local",
                    "variables": [{"name": "PGADMIN_CONFIG_MAX_LOGIN_ATTEMPTS", "value": 25}]
            },
            "image": {"tag": "8.4"},
            "existingSecret": "pgadmin4-password",
            "secretKeys": {"pgadminPasswordKey": "password"},
            "service": {"type": "ClusterIP"},
            "resources": {
                "limits": {
                    "cpu": self.config.resources.cpu,
                    "memory": self.config.resources.memory,
                },
                "requests": {
                    "cpu": self.config.resources.cpu,
                    "memory": self.config.resources.memory,
                },
            },
            "ingress": {
                "enabled": True,
                "annotations": {
                    "cert-manager.io/cluster-issuer": "letsencrypt",
                    "external-dns.alpha.kubernetes.io/hostname": f"pgadmin-{self.args.cluster}.local",
                    "external-dns/passthrough-record": "true",
                    "kubernetes.io/ingress.class": "nginx-private",
                    "kubernetes.io/tls-acme": "true",
                },
                "hosts": [
                    {
                        "host": f"pgadmin-{self.args.cluster}.local",
                        "paths": [
                            {"path": '/',
                             "pathType": "ImplementationSpecific"}
                        ],
                    }
                ],
                "tls": [
                    {
                        "hosts": [f"pgadmin-{self.args.cluster}.local"],
                        "secretName": "pgadmin-tls",
                    }
                ],
            },
        }

        if self.kwargs.get("provider") == "gcp":
            values["nodeSelector"] = {"nodegroup": "addons"}

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "pgadmin",
            "release": f"pgadmin",
        }
        if action != "delete":
            params["chart"] = "runix/pgadmin4"
            params["values"] = "values.yaml"
            params["version"] = self.config.version
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def pgadmin_password_secret(self, action):
        """
        Create the pgadmin secrets file, and generate the needed password.
        """
        secrets = {
            "apiVersion": "v1",
            "kind": "Secret",
            "type": "Opaque",
            "metadata": {"name": "pgadmin4-password", "namespace": "pgadmin"},
            "data": {
                "password": base64.encodebytes(utils.gen_password(64, special_characters=False)),
            },
        }
        with open("secrets.yaml", "w") as f:
            YAML().dump(secrets, f)

        kubectl(action=action, filename="secrets.yaml")
        os.unlink("secrets.yaml")

    def upgrade(self):
        """
        Upgrade the chart installs.
        """
        self.pgadmin(action="upgrade")
