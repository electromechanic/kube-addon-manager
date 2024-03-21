import base64
import logging
import os
import time

from manager import BaseManager, helm, kubectl, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.config = self.kwargs.get("config")
        self.issuers = [i.name for i in self.config.cluster_issuer.issuers]

    def cert_manager(self, issuer, action="upgrade"):
        """
        Installs the cert manager addon.  This is used for programatic auto handling of cert issuing
        and renewal.
        """
        values = {
            "installCRDs": True,
            "serviceAccount": {
                "create": True,
                "name": "cert-manager",
            },
            "securityContext": {"fsGroup": 1000},
        }
        if "letsencrypt" in issuer:
            values["ingressShim"] = {
                "defaultIssuerName": issuer,
                "defaultIssuerKind": "ClusterIssuer",
                "defaultIssuerGroup": "cert-manager.io",
            }
            values["extraArgs"] = [
                "--dns01-recursive-nameservers-only",
                '--dns01-recursive-nameservers="8.8.8.8:53"',
            ]

        if self.kwargs.get("provider") == "gcp":
            values["nodeSelector"] = {"nodegroup": "addons"}

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {"action": action, "namespace": "cert-manager", "release": "cert-manager"}
        if action != "delete":
            params["chart"] = "jetstack/cert-manager"
            params["values"] = "values.yaml"
            params["version"] = self.config.version
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def cert_manager_approle_secret(self, action="create"):
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
                "name": "cert-manager-vault-approle",
                "namespace": "cert-manager",
            },
            "data": {
                "secretId": base64.b64encode(os.getenv("VAULT_APPROLE_SECRET_ID").encode("utf-8"))
            },
        }
        with open("secret.yaml", "w") as f:
            YAML().dump(secret, f)

        kubectl(action=action, filename="secret.yaml")

    def cert_manager_clusterissuer(self, issuer, action="create"):
        """
        Create the letsencrypt clusterissuer for use with cert-manager.
        """
        # Uncomment chain if we switch main Vault certificate to being issued by private CA
        # with open(f'{os.getenv("HOME")}/ca-chain.pem') as f:
        #    chain = f.read()
        for cluster_issuer in self.config.cluster_issuer.issuers:
            if issuer == cluster_issuer.name:
                config = cluster_issuer

        if config.type == "acme":
            spec = {
                "apiVersion": "cert-manager.io/v1",
                "kind": "ClusterIssuer",
                "metadata": {"name": config.name},
                "spec": {
                    "acme": {
                        "email": config.email,
                        "server": config.server,
                        "preferredChain": "ISRG Root X1",
                        "privateKeySecretRef": {"name": f"{config.name}-account-key"},
                        "solvers": [
                            {
                                "selector": {"dnsZones": config.zones},
                                "dns01": {
                                    "cloudflare": {
                                        "email": config.email,
                                        "apiTokenSecretRef": {
                                            "name": "cloudflare-api-key-secret",
                                            "key": "api-key",
                                        },
                                    }
                                },
                            },
                        ],
                    }
                },
            }

        if config.type == "vault":
            spec = {
                "apiVersion": "cert-manager.io/v1",
                "kind": "ClusterIssuer",
                "metadata": {
                    "name": config.name,
                },
                "spec": {
                    "vault": {
                        "path": f"pki/sign/{config.role}",
                        "server": config.server,
                        # "caBundle": base64.encodebytes(chain.encode("utf-8")),
                        "auth": {
                            "appRole": {
                                "path": "approle",
                                "roleId": os.getenv("VAULT_APPROLE_ROLE_ID"),
                                "secretRef": {
                                    "name": "cert-manager-vault-approle",
                                    "key": "secretId",
                                },
                            }
                        },
                    }
                },
            }

        if config.type == "private":
            spec = {
                "apiVersion": "cert-manager.io/v1",
                "kind": "ClusterIssuer",
                "metadata": {
                    "name": config.name,
                },
                "spec": {"ca": {"secretName": config.secret}},
            }

        with open("cluster_issuer.yaml", "w") as f:
            YAML().dump(spec, f)

        kubectl(action=action, namespace="cert-manager", filename="cluster_issuer.yaml")
        os.unlink("cluster_issuer.yaml")

    def cert_manager_cloudflare_secret(self, action="create"):
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
                "name": "cloudflare-api-key-secret",
                "namespace": "cert-manager",
            },
            "data": {"api-key": base64.b64encode(os.getenv("CF_API_KEY").encode("utf-8"))},
        }
        with open("secret.yaml", "w") as f:
            YAML().dump(secret, f)

        kubectl(action=action, filename="secret.yaml")
        os.unlink("secret.yaml")

    def cert_manager_sisu_ca_secret(self, action="create"):
        """
        Create kubernetes secret with the secret_id for the vault approle auth.
        """
        for cluster_issuer in self.config.cluster_issuer.issuers:
            if cluster_issuer.name == "sisu-ca":
                config = cluster_issuer
        if action not in ["create", "apply", "delete"]:
            raise ValueError("action must be create, apply, or delete.")
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "type": "Opaque",
            "metadata": {
                "name": config.secret,
                "namespace": "cert-manager",
            },
            "data": {"tls.crt": os.getenv("SISU_CA_CERT"), "tls.key": os.getenv("SISU_CA_KEY")},
        }
        with open("secret.yaml", "w") as f:
            YAML().dump(secret, f)

        kubectl(action=action, filename="secret.yaml")
        os.unlink("secret.yaml")

    def delete(self, issuer="letsencrypt"):
        """
        Delete the cert-manager addon.
        """
        for issuer in self.issuers:
            self.cert_manager_clusterissuer(issuer, action="delete")
        self.cert_manager_cloudflare_secret(action="delete")
        self.cert_manager_sisu_ca_secret(action="delete")
        self.cert_manager(issuer, action="delete")

    def install(self, issuer="letsencrypt"):
        """
        Logic for the installation of the cert-manager.
        """
        self.cert_manager(issuer, action="upgrade")

        # Allow cert-manager pods to start
        time.sleep(30)
        self.cert_manager_cloudflare_secret(action="create")
        self.cert_manager_sisu_ca_secret(action="create")
        for issuer in self.issuers:
            self.cert_manager_clusterissuer(issuer, action="create")

    def upgrade(self, issuer="letsencrypt"):
        """
        Upgrade the cert-manager install.
        """
        self.cert_manager(issuer, action="upgrade")
        self.cert_manager_cloudflare_secret(action="apply")
        self.cert_manager_sisu_ca_secret(action="apply")
        for issuer in self.issuers:
            self.cert_manager_clusterissuer(issuer, action="apply")
