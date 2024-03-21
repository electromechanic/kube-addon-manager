import logging
import os
import subprocess
import time

from manager import BaseManager, helm, kubectl, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.args = self.kwargs.get("args")
        self.cluster = self.args.cluster
        self.config = self.kwargs.get("config")
        self.provider = self.args.providers

    def delete(self, issuer="letsencrypt"):
        """
        Delete the nginx-ingress addon.
        """
        for endpoint in self.config.endpoints:
            self.nginx_ingress(endpoint, action="delete")
        self.nginx_ingress_default_certificate(
            self.config.get("issuer", "letsencrypt"), action="delete"
        )

    def install(self, issuer="letsencrypt"):
        """
        Logic for the initial installation of the nginx-ingress controllers.
        """
        if self.provider == "gcp":
            self.nginx_ingress_backendconfig(action="create")
        self.nginx_ingress_default_certificate(self.config.get("issuer", "letsencrypt"))

        # setup poll loop to detect successful issuing of certificate
        # using subprocess as this is a CRD and not dug in enough to handle in python k8s client
        certificate = f"wildcard.{self.cluster}"
        status = "False"
        count = 0
        sleep = 45
        command = subprocess.getoutput("which kubectl")
        while status == "False":
            results = subprocess.check_output(
                [command, "-n", "nginx-ingress", "get", "certificate"],
                encoding="utf-8",
            ).split("\n")
            for line in results:
                if certificate in line:
                    status = line.split()[1]
                    logger.info("%s certificate status is %s", certificate, status)
                    if status == "True":
                        # Still sleeps a little to make sure cert secret gets created before install
                        sleep = 5
                        break
            time.sleep(sleep)
            count += 1
            if count == 20:
                kubectl(
                    action="describe",
                    namespace="nginx-ingress",
                    resource=f"certificate wildcard.{self.cluster}",
                )
                kubectl(action="logs", namespace="cert-manager", resource="-l app=cert-manager")
                raise Exception(f"{issuer} wildcard certificate validation has failed.")

        for endpoint in self.config.endpoints:
            self.nginx_ingress(endpoint)

    def nginx_ingress(self, endpoint, action="upgrade"):
        """
        Install the official nginx ingress controller. Using a file for values as helm set commands
        result in invalid parsing for all of the annotations.
        """
        if endpoint not in ["public", "private"]:
            raise ValueError("Invalid value for endpoint, must be public or private.")

        if endpoint == "public":
            dns_record = "proxied"
        if endpoint == "private":
            dns_record = "passthrough"

        values = {
            "controller": {
                "name": f"nginx-{endpoint}",
                "rbac": {"create": "true"},
                "ingressClass": f"nginx-{endpoint}",
                "ingressClassResource": {
                    "name": f"nginx-{endpoint}",
                    "enabled": True,
                    "default": False,
                    "controllerValue": "k8s.io/ingress-nginx",
                },
                "extraArgs": {
                    "default-ssl-certificate": "nginx-ingress/nginx-ingress-wildcard",
                },
                "resources": {
                    "limits": {"cpu": "1000m", "memory": "2048Mi"},
                    "requests": {"cpu": "100m", "memory": "204Mi"},
                },
                "autoscaling": {
                    "enabled": "true",
                    "minReplicas": "1",
                    "maxReplicas": "12",
                    "targetCPUUtilizationPercentage": "65",
                    "targetMemoryUtilizationPercentage": "65",
                },
                "service": {
                    "annotations": {
                        "external-dns.alpha.kubernetes.io/hostname": f"nginx-{endpoint}.{self.cluster}.{self.config.zones[0]}",
                        f"external-dns/{dns_record}-record": "true",
                    },
                    "externalTrafficPolicy": "Local",
                },
                "metrics": {
                    "enabled": True,
                    "service": {
                        "annotations": {
                            "prometheus.io/port": "10254",
                            "prometheus.io/scrape": "true",
                        }
                    },
                },
            }
        }

        hostnames = [f"nginx-{endpoint}.{self.cluster}.{self.config.zones[0]}"]

        if endpoint == "public":
            values["controller"]["service"]["loadBalancerSourceRanges"] = self.config.cloudflare_ips

        if endpoint == "private":
            values["tcp"] = self.config.additional_ports.tcp.to_dict()
            for hostname in self.config.additional_dns:
                hostnames.append(f"{hostname}.{self.cluster}.{self.config.zones[0]}")

        values["controller"]["service"]["annotations"][
            "external-dns.alpha.kubernetes.io/hostname"
        ] = ",".join(hostnames)

        if self.provider == "aws":
            values["controller"]["service"]["annotations"][
                "service.beta.kubernetes.io/aws-load-balancer-type"
            ] = "nlb-ip"
            values["controller"]["service"]["annotations"][
                "service.beta.kubernetes.io/aws-load-balancer-backend-protocol"
            ] = "tcp"
            values["controller"]["service"]["annotations"][
                "service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled"
            ] = "true"
            values["controller"]["service"]["annotations"][
                "service.beta.kubernetes.io/aws-load-balancer-connection-idle-timeout"
            ] = "3600"
            values["controller"]["service"]["annotations"][
                "service.beta.kubernetes.io/aws-load-balancer-connection-draining-timeout"
            ] = "60"

            if endpoint == "private":
                values["controller"]["service"]["annotations"][
                    "service.beta.kubernetes.io/aws-load-balancer-scheme"
                ] = "internal"

        if self.provider == "gcp":
            values["nodeSelector"] = {"nodegroup": "addons"}
            values["controller"]["service"]["annotations"][
                "cloud.google.com/backend-config"
            ] = '{"ports": {"80":"nginx-ingress-backendconfig"}}'

            if endpoint == "private":
                values["controller"]["service"]["annotations"][
                    "networking.gke.io/load-balancer-type"
                ] = "Internal"

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "nginx-ingress",
            "release": f"nginx-ingress-{endpoint}",
        }
        if action != "delete":
            params["chart"] = "ingress_nginx/ingress-nginx"
            params["values"] = "values.yaml"
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def nginx_ingress_backendconfig(self, action="create"):
        """
        Handle the backendconfig that will set timeout for the load balancers.
        """
        spec = {
            "apiVersion": "cloud.google.com/v1",
            "kind": "BackendConfig",
            "metadata": {"name": "nginx-ingress-backendconfig", "namespace": "nginx-ingress"},
            "spec": {"timeoutSec": 600},
        }

        with open("nginx-ingress-backendconfig.yaml", "w") as f:
            YAML().dump(spec, f)

        kubectl(action=action, filename="nginx-ingress-backendconfig.yaml")
        os.unlink("nginx-ingress-backendconfig.yaml")

    def nginx_ingress_default_certificate(self, issuer="letsencrypt", action="create"):
        """
        Obtain the certificate from letsencrypt to use as the default certificate on the ingress.
        """
        domain = self.config.zones[0]
        domains = []
        for dom in self.config.zones:
            domains.append(f"*.{dom}")
            domains.append(f"*.{self.cluster}.{dom}")
        certificate = {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": f"wildcard.{self.cluster}",
                "namespace": "nginx-ingress",
            },
            "spec": {
                "secretName": "nginx-ingress-wildcard",
                "commonName": f"*.{domain}",
                "issuerRef": {"name": issuer, "kind": "ClusterIssuer", "group": "cert-manager.io"},
                "dnsNames": domains,
            },
        }
        with open("nginx-ingress-wildcard.yaml", "w") as f:
            YAML().dump(certificate, f)

        kubectl(action=action, filename="nginx-ingress-wildcard.yaml")
        os.unlink("nginx-ingress-wildcard.yaml")

    def upgrade(self, issuer="letsencrypt"):
        """
        Logic for the upgrade of the nginx-ingress controllers.
        """
        self.nginx_ingress_default_certificate(
            self.config.get("issuer", "letsencrypt"), action="apply"
        )
        if self.provider == "gcp":
            self.nginx_ingress_backendconfig(action="apply")
        for endpoint in self.config.endpoints:
            self.nginx_ingress(endpoint)
