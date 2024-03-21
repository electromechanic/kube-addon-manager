import json
import logging
import os
import sys
import time

import boto3
from manager import BaseManager, helm
from manager.utils import objectify, run_command
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.args = self.kwargs.get("args")
        self.provider = self.args.providers

        if self.provider == "aws":
            self.cluster = self.args.cluster
            self.config = self.kwargs.get("config")
            self.iam = boto3.client("iam")
            self.region = self.args.region
            self.sts = boto3.client("sts")

    def cluster_autoscaler(self, action="upgrade"):
        """
        Install the cluster autoscaler.
        """
        values = {
            "autoDiscovery": {"clusterName": self.cluster},
            "cloudProvider": "aws",
            "awsRegion": self.region,
            "replicaCount": 3,
            "rbac": {"serviceAccount": {"create": False, "name": "cluster-autoscaler"}},
            "resources": {
                "limits": {"cpu": "1000m", "memory": "3Gi"},
                "requests": {"cpu": "125m", "memory": "375Mi"},
            },
            # "nodeSelector": {"nodegroup": "kube-addons"},
        }
        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "cluster-autoscaler",
            "release": "cluster-autoscaler",
        }
        if action != "delete":
            params["chart"] = "autoscaler/cluster-autoscaler"
            params["values"] = "values.yaml"
            logger.info("Values for helm chart are: %s", values)

        helm(**params)
        os.unlink("values.yaml")

    def delete(self):
        """
        Delete the cluster-autoscaler addon.
        """
        if self.provider == "aws":
            self.cluster_autoscaler(action="delete")
            self.delete_iam_service_account("cluster-autoscaler", "cluster-autoscaler")
            self.delete_fargateprofile("cluster-autoscaler")

    def install(self):
        """
        Logic for the initial installation of the cluster-autoscaler.
        """
        if self.provider == "aws":
            self.create_iam_service_account("cluster-autoscaler", "cluster-autoscaler")
            self.create_fargate_profile("cluster-autoscaler", "cluster-autoscaler")
            self.cluster_autoscaler(action="upgrade")

    def create_iam_service_account_iam_policy(self, service_account):
        """
        Create the IAM policy that will be bound to the eks service account.
        """
        policy_name = f"{self.cluster}-{self.region}-{service_account}"
        try:
            account_id = self.sts.get_caller_identity()["Account"]
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            if self.iam.get_policy(PolicyArn=policy_arn)["Policy"]:
                return policy_arn
        except Exception as err:
            logger.error(err)

        with open(f"assets/iam_policies/{service_account}-iam-policy.json") as f:
            iam_policy = json.loads(f.read())

        response = objectify(
            self.iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(iam_policy),
            )
        )
        return response.Policy.Arn

    def create_iam_service_account(self, service_account, namespace, iam_policy_arn=None):
        """
        Create the iam service account using eksctl.
        """
        if iam_policy_arn is None:
            iam_policy_arn = self.create_iam_service_account_iam_policy(service_account)
        logger.info(
            [
                "/usr/local/bin/eksctl",
                "create",
                "iamserviceaccount",
                "--cluster",
                self.cluster,
                "--region",
                self.region,
                "--namespace",
                namespace,
                "--name",
                service_account,
                "--attach-policy-arn",
                iam_policy_arn,
                "--approve",
            ]
        )
        run_command(
            [
                "/usr/local/bin/eksctl",
                "create",
                "iamserviceaccount",
                "--cluster",
                self.cluster,
                "--region",
                self.region,
                "--namespace",
                namespace,
                "--name",
                service_account,
                "--attach-policy-arn",
                iam_policy_arn,
                "--approve",
            ]
        )

    def delete_iam_policy(self, name):
        """
        Delete the specified policy that was used the service account.
        """
        policy = f"{self.cluster}-{self.region}-{name}"
        policies = self.iam.list_policies(Scope="Local").get("Policies")
        try:
            arn = [p.get("Arn") for p in policies if p["PolicyName"] == policy][0]
            count = 6
            wait = 10
            attached = True
            while attached is True:
                status = self.iam.get_policy(PolicyArn=arn)
                if status["Policy"]["AttachmentCount"] == 0:
                    wait = 0
                    attached = False
                else:
                    count += 1
                    time.sleep(wait)
                    if count <= 6:
                        logging.error(
                            "Policy %s is still attached to %s entities.",
                            arn,
                            status["Policy"]["AttachmentCount"],
                        )
                        sys.exit(1)
            self.iam.delete_policy(PolicyArn=arn)
            logger.info("Deleted IAM policy for service account: %s", arn)
        except IndexError:
            logging.error("Policy %s does not exist.", policy)

    def delete_iam_service_account(self, service_account, namespace):
        """
        Create the iam service account using eksctl.
        """
        run_command(
            [
                "/usr/local/bin/eksctl",
                "delete",
                "iamserviceaccount",
                "--cluster",
                self.cluster,
                "--region",
                self.region,
                "--namespace",
                namespace,
                "--name",
                service_account,
            ]
        )
        self.delete_iam_policy(service_account)
