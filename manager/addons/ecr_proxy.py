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
        Delete the ecr_proxy addon.
        """
        self.ecr_proxy(action="delete")
        self.ecr_creds_secret(action="delete")
        self.ecr_proxy_certificate(action="delete")

    def install(self):
        """
        Logic for the installation of ecr_proxy.
        """
        self.ecr_proxy_certificate(action="create")
        self.ecr_creds_secret(action="create")
        self.ecr_proxy(action="install")

    def upgrade(self):
        """
        Upgrade the chart installs.
        """
        self.ecr_proxy_certificate(action="apply")
        self.ecr_creds_secret(action="apply")
        self.ecr_proxy(action="upgrade")

    def ecr_creds_secret(self, action="create"):
        """
        Create kubernetes secret with the secret_id for the vault approle auth.
        """
        if action not in ["create", "apply", "delete"]:
            raise ValueError("action must be create, apply, or delete.")
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "type": "Opaque",
            "metadata": {
                "name": "ecr-credentials",
                "namespace": "ecr-proxy",
            },
            "data": {
                "access-key": base64.b64encode(os.getenv("ECR_ACCESS_KEY").encode("utf-8")),
                "secret-key": base64.b64encode(os.getenv("ECR_SECRET_ACCESS_KEY").encode("utf-8")),
            },
        }
        with open("secret.yaml", "w") as f:
            YAML().dump(secret, f)

        kubectl(action=action, filename="secret.yaml")

    def ecr_proxy(self, action="upgrade"):
        """
        Handle the values file.
        """
        values = {
            "env": [
                {"name": "UPSTREAM", "value": f"https://{self.config.get('ecr_registry')}"},
                {"name": "AWS_REGION", "value": self.config.get("ecr_registry").split(".")[3]},
                {
                    "name": "AWS_ACCESS_KEY_ID",
                    "valueFrom": {"secretKeyRef": {"name": "ecr-credentials", "key": "access-key"}},
                },
                {
                    "name": "AWS_SECRET_ACCESS_KEY",
                    "valueFrom": {"secretKeyRef": {"name": "ecr-credentials", "key": "secret-key"}},
                },
                {"name": "RESOLVER", "value": "kube-dns.kube-system.svc.cluster.local"},
            ],
            "ingress": {
                "enabled": True,
                "annotations": {
                    "cert-manager.io/cluster-issuer": "letsencrypt",
                    "external-dns.alpha.kubernetes.io/hostname": f"ep-{self.args.cluster}.sisu.ai",
                    "external-dns/passthrough-record": "true",
                    "kubernetes.io/ingress.class": "nginx-private",
                    "kubernetes.io/tls-acme": "true",
                },
                "hosts": [
                    {
                        "host": f"ep-{self.args.cluster}.sisu.ai",
                        "paths": ["/"],
                    }
                ],
                "tls": [
                    {
                        "hosts": [f"ep-{self.args.cluster}.sisu.ai"],
                        "secretName": "kube-ecr-proxy-tls",
                    }
                ],
            },
            "replicaCount": "1",
        }

        if self.args.providers == "gcp":
            values["nodeSelector"] = {"nodegroup": "addons"}
            # values["ingress"]["annotations"]["kubernetes.io/ingress.class"] = "gce-internal"
            # values["ingress"]["annotations"]["kubernetes.io/ingress.allow-http"] = "false"

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "ecr-proxy",
            "release": "kube",
        }
        if action != "delete":
            params["chart"] = "evryfs/ecr-proxy"
            params["values"] = "values.yaml"
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def ecr_proxy_certificate(self, issuer="letsencrypt", action="create"):
        """
        Obtain the certificate from letsencrypt to use as the default certificate on the ingress.
        """
        certificate = {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": "kube-ecr-proxy-tls",
                "namespace": "ecr-proxy",
            },
            "spec": {
                "secretName": "kube-ecr-proxy-tls",
                "commonName": f"ep-{self.args.cluster}.sisu.ai",
                "issuerRef": {"name": issuer, "kind": "ClusterIssuer", "group": "cert-manager.io"},
                "dnsNames": [f"ep-{self.args.cluster}.sisu.ai"],
            },
        }
        with open("ecr-proxy.yaml", "w") as f:
            YAML().dump(certificate, f)

        kubectl(action=action, filename="ecr-proxy.yaml")
        os.unlink("ecr-proxy.yaml")
