import base64
import logging
import os
import subprocess

import requests
from manager import BaseManager, helm, kubectl, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.args = self.kwargs.get("args")
        self.config = self.kwargs.get("config")
        self.endpoint = self.config.get("endpoint", "private")

    def delete(self):
        """
        Delete the openunison addon.
        """
        helm(action="delete", namespace="openunison", chart="orchestra-login-googlews")
        helm(action="delete", namespace="openunison", chart="orchestra-login-portal")
        helm(action="delete", namespace="openunison", chart="orchestra")
        helm(action="delete", namespace="openunison", chart="openunison")

    def install(self):
        """
        Logic for the initial installation of openunison.
        """
        self.openunison_svc_account()
        self.openunison()
        self.openunison_admin_bindings("create", f"cloud-infra")

    def openunison_admin_bindings(self, action, admin_group):
        """
        Create the cluster role bindings for the admin group.
        """
        cluster_role_binding = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRoleBinding",
            "metadata": {"name": "sisu-cluster-admins"},
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "ClusterRole",
                "name": "cluster-admin",
            },
            "subjects": [{"kind": "Group", "name": admin_group}],
        }
        with open("cluster-admins.yaml", "w") as f:
            YAML().dump(cluster_role_binding, f)

        kubectl(action=action, filename="cluster-admins.yaml")
        os.unlink("cluster-admins.yaml")

    def openunison(self):
        if self.endpoint == "public":
            dns_type = "proxied"
        if self.endpoint == "private":
            dns_type = "passthrough"

        values = {
            "cert_template": {
                "ou": self.args.cluster,
                "o": "Sisu",
                "l": "San Francisco",
                "st": "CA",
                "c": "USA",
            },
            "certs": {"use_k8s_cm": False},
            "dashboard": {
                "enabled": False,
                # "namespace": "dashboard",
                # "cert_name": "kubernetes-dashboard-certs",
                # "label": "app.kubernetes.io/instance=dashboard",
                # "service_name": "dashboard-kubernetes-dashboard-web",
                # "require_session": True,
            },
            "enable_impersonation": True,
            "google_ws": {
                "admin_email": "sso@sisudata.com",
                "service_account_email": self.config.get("service_account_email"),
            },
            "image": "docker.io/tremolosecurity/openunison-k8s",
            "impersonation": {
                "use_jetstack": True,
                "jetstack_oidc_proxy_image": "docker.io/tremolosecurity/kube-oidc-proxy:latest",
                "explicit_certificate_trust": True,
            },
            "k8s_cluster_name": self.args.cluster,
            "monitoring": {
                "prometheus_service_account": "system:serviceaccount:monitoring:prometheus-k8s"
            },
            "myvd_config_path": "WEB-INF/myvd.conf",
            "network": {
                "openunison_host": f"ou.{self.args.cluster}.sisu.ai",
                "dashboard_host": f"dashboard.{self.args.cluster}.sisu.ai",
                "api_server_host": f"api.{self.args.cluster}.sisu.ai",
                "session_inactivity_timeout_seconds": 3600,
                "createIngressCertificate": False,
                "ingress_type": "nginx",
                "ingress_annotations": {
                    "kubernetes.io/ingress.class": f"nginx-{self.endpoint}",
                    "cert-manager.io/cluster-issuer": "letsencrypt",
                    f"external-dns/{dns_type}-record": "true",
                },
            },
            "oidc": {
                "client_id": self.config.get("oauth_client_id"),
                "issuer": "https://accounts.google.com",
                "user_in_idtoken": False,
                "domain": "",
                "scopes": "openid email profile",
                "claims": {
                    "sub": "email",
                    "email": "email",
                    "given_name": "given_name",
                    "family_name": "family_name",
                    "display_name": "name",
                    "groups": "groups",
                },
            },
            "openunison": {
                "enable_provisioning": False,
                "html": {"image": "docker.io/tremolosecurity/openunison-k8s-html"},
                "include_auth_chain": "google-ws-load-groups",
                "non_secret_data": {
                    "K8S_DB_SSO": "oidc",
                    "PROMETHEUS_SERVICE_ACCOUNT": "system:serviceaccount:monitoring:prometheus-k8s",
                    "SHOW_PORTAL_ORGS": "false",
                },
                "replicas": 1,
                "secrets": [],
                "use_standard_jit_workflow": True,
            },
        }
        with open("values.yaml", "w") as f:
            YAML().dump(values, f)
        logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        client_secret = os.getenv("OAUTH_CLIENT_SECRET")
        with open("oauth_client_secret.yaml", "w") as f:
            f.write(client_secret)

        command = [
            subprocess.getoutput("which ouctl"),
            "install-auth-portal",
            "-s",
            "oauth_client_secret.yaml",
            "-r",
            "orchestra-login-googlews=tremolo/orchestra-login-googlews",
            "values.yaml",
        ]
        utils.run_command(command)

    def openunison_svc_account(self, action="apply"):
        """
        Create a secret containing the private key for the google service account.
        """
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "googlews", "namespace": "openunison"},
            "type": "Opaque",
            "data": {"key": os.getenv("OPENUNISON_SVC_ACCOUNT")},
        }

        with open("openunison_svc_account.yaml", "w") as f:
            YAML().dump(secret, f)

        kubectl(action=action, filename="openunison_svc_account.yaml")
        os.unlink("openunison_svc_account.yaml")

    def upgrade(self):
        """
        Logic for the initial installation of openunison.
        """
        self.openunison_svc_account()
        self.openunison()
        self.openunison_admin_bindings("apply", f"cloud-infra")
