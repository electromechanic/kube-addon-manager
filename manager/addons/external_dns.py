import logging
import os

from manager import BaseManager, helm, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.args = self.kwargs.get("args")
        self.config = self.kwargs.get("config")

    def external_dns(self, domains, zone_type, action="upgrade"):
        """
        Install external-dns.
        """
        values = {
            "domainFilters": domains,
            "provider": "cloudflare",
            "annotationFilter": f"external-dns/{zone_type}-record=true",
            "policy": "sync",
            "registry": "txt",
            "txtOwnerId": f"{self.args.cluster}-{zone_type}",
            "interval": "3m",
            "cloudflare": {
                "email": self.config.cloudflare_email,
                "apiToken": os.getenv("CF_API_KEY"),
            },
        }

        if zone_type == "proxied":
            values["cloudflare"]["proxied"] = True

        if zone_type == "passthrough":
            values["cloudflare"]["proxied"] = False

        if self.kwargs.get("provider") == "gcp":
            values["nodeSelector"] = {"nodegroup": "addons"}

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "external-dns",
            "release": f"external-dns-{zone_type}-zones",
        }
        if action != "delete":
            params["chart"] = "bitnami/external-dns"
            params["values"] = "values.yaml"
            params["version"] = self.config.version
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def delete(self):
        """
        Delete the external-dns addon.
        """
        self.external_dns(self.config.zones, "passthrough", action="delete")
        self.external_dns(self.config.zones, "proxied", action="delete")

    def install(self):
        """
        Logic for the installation of external-dns.
        """
        self.external_dns(self.config.zones, "proxied")
        self.external_dns(self.config.zones, "passthrough")

    def upgrade(self):
        """
        Upgrade the chart installs.
        """
        self.external_dns(self.config.zones, "proxied")
        self.external_dns(self.config.zones, "passthrough")
