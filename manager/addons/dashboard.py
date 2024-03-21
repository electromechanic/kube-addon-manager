import logging
import os

from manager import BaseManager, helm, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def dashboard(self, action="upgrade"):
        """
        Install the kubernetes dashboard.
        """
        values = {
            "rbac": {"create": True},
            "serviceAccount": {"create": True, "name": "k8s-dasboard"},
            "nodeSelector": {"nodegroup": "addons"},
            "cert-manager": {"enabled": False},
            "nginx": {"enabled": False},
            "metrics-server": {"enabled": False},
        }
        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "dashboard",
            "release": "dashboard",
        }
        if action != "delete":
            params["chart"] = "kubernetes_dashboard/kubernetes-dashboard"
            params["values"] = "values.yaml"
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def delete(self):
        """
        Delete the dashboard addon.
        """
        self.dashboard(action="delete")

    def install(self):
        """
        Logic for the initial installation of the kubernetes-dashboard.
        """
        self.dashboard(action="upgrade")
