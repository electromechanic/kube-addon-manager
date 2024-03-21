import logging

import manager.addons
import manager.utils as utils
from dotted_dict import PreserveKeysDottedDict as dd

from . import BaseManager, helm, kubectl

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        """
        Class to install via helm charts all core addons to complete our kube creation.
        """
        self.args = self.kwargs.get("args")
        self.config = self.kwargs.get("config")

        self.add_helm_repos(self.config.helm.repos.items())

        self.addons = {}
        for addon in self.order_addons():
            self.addons[addon] = getattr(manager.addons, addon).Manager(
                args=self.args, config=self.config.addons.get(addon)
            )

    def add_helm_repos(self, repos):
        """
        Take list of repos [(name, url)] to add to helm in container.
        """
        for repo in repos:
            helm(action=f"repo add {repo[0]} {repo[1]}", noout=True)
        # helm(action="repo update", noout=True)
        helm(action="repo update")

    def delete(self, service):
        """
        Delete the specified addon. If all, delete all addons.
        """
        service = service.replace("-", "_")
        if service == "all":
            for name, manager in list(self.addons.items())[::-1]:
                manager.delete()
                self.namespace("delete", name)
        else:
            self.addons[service].delete()
            self.namespace("delete", service)

    def install(self, service="all"):
        """
        Install all defined addons.
        """
        service = service.replace("-", "_")
        if service == "all":
            for service, manager in self.addons.items():
                self.namespace("create", service)
                manager.install()
        else:
            self.namespace("create", service)
            try:
                self.addons[service].install()
            except KeyError as err:
                logging.error("%s is not a valid addon name", service)

    def namespace(self, action, namespace):
        """
        Take specified action on the specified namespace.
        """
        namespace = namespace.replace("_", "-")
        kubectl(action=action, resource=f"namespace {namespace}")

    def order_addons(self):
        """
        Handle processing of addons to order for use. Handles enable and dependency resolution.
        """
        addons = [a for a in dir(manager.addons) if a[0] != "_"]
        enable = []
        disabled = []
        if self.args.providers == "aws":
            enable.append("cluster_autoscaler")
        while (len(enable) + len(disabled)) != len(addons):
            for addon in addons:
                if addon in enable or addon in disabled:
                    continue
                config = self.config.addons.get(addon, dd({"enabled": True}))
                if config.enabled is True:
                    if config.get("depends_on", None):
                        found = True
                        for dep in config.depends_on:
                            dep = dep.replace("-", "_")
                            if dep not in enable:
                                found = False
                                break
                        if found:
                            if addon not in enable:
                                enable.append(addon)
                    else:
                        if addon not in enable:
                            enable.append(addon)
                else:
                    if addon not in disabled:
                        disabled.append(addon)
        return enable

    def upgrade(self, service="all"):
        """
        Install all defined addons.
        """
        service = service.replace("-", "_")
        if service == "all":
            for service, manager in self.addons.items():
                manager.upgrade()
        else:
            self.addons[service].upgrade()
