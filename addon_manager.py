#! /usr/bin/env python3

import argparse
import logging
import os
import subprocess
import sys

from manager.kube import Manager
from manager.utils import objectify, run_command
from ruamel.yaml import YAML

logging.basicConfig(
    level=logging.INFO,
    format=("%(asctime)s [%(levelname)s] %(message)s"),
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def arguments():
    """
    Init argparer and parse arguments.
    """
    parser = argparse.ArgumentParser(
        description="Manage the kubernetes addons that make the platform for our clusters."
    )

    parser.add_argument(
        "--config-file",
        action="store",
        dest="config",
        default="config.yaml",
        type=str,
        help="The config file to load.",
    )

    subparsers = parser.add_subparsers(dest="providers")

    aws = subparsers.add_parser("aws", help="Enter options for AWS hosted kubes.")

    aws.add_argument(
        "-a",
        "--action",
        action="store",
        choices=["create", "delete", "upgrade"],
        dest="action",
        default=os.getenv("ACTION"),
        type=str,
    )
    aws.add_argument(
        "-c",
        "--cluster",
        action="store",
        dest="cluster",
        default=os.getenv("CLUSTER"),
        type=str,
        help="""The k8s cluster to manage addons for.If not specified, uses CLUSTER environment
            variable.""",
    )
    aws.add_argument(
        "-e",
        "--environment",
        action="store",
        choices=["default", "dev", "prod"],
        dest="environment",
        default=os.getenv("ENVIRONMENT", "default"),
        type=str,
        help="""The AWS account to use, maps to the profile in your ~/.aws/credentials file. If not
            specified uses the ENVIRONMENT environment variable.""",
    )
    aws.add_argument(
        "-n",
        "--name",
        action="store",
        dest="name",
        default=os.getenv("NAME", "all"),
        type=str,
        help="""The name of the resource to work on. If you specify all, it will modify all of the
            addons on the cluster. If not specified, uses NAME environment variable.""",
    )
    aws.add_argument(
        "-r",
        "--region",
        action="store",
        dest="region",
        default=os.getenv("REGION", "us-west-2"),
        type=str,
        help="""The region location of the k8s cluster. If not specified, uses REGION environment
            variable.""",
    )

    gcp = subparsers.add_parser("gcp", help="Enter options for google hosted kubes.")

    gcp.add_argument(
        "-a",
        "--action",
        action="store",
        choices=["create", "delete", "upgrade"],
        dest="action",
        default=os.getenv("ACTION"),
        type=str,
    )
    gcp.add_argument(
        "-c",
        "--cluster",
        action="store",
        dest="cluster",
        default=os.getenv("CLUSTER"),
        type=str,
        help="""The k8s cluster to manage addons for.If not specified, uses CLUSTER environment
            variable.""",
    )
    gcp.add_argument(
        "-n",
        "--name",
        action="store",
        dest="name",
        default=os.getenv("NAME", "all"),
        type=str,
        help="""The name of the resource to work on. If you specify all, it will modify all of the
            addons on the cluster. If not specified, uses NAME environment variable.""",
    )
    gcp.add_argument(
        "-p",
        "--project",
        action="store",
        dest="project",
        default=os.getenv("PROJECT"),
        type=str,
        help="""The GCP project of the k8s cluster. If not specified, uses PROJECT environment
            variable.""",
    )
    gcp.add_argument(
        "-r",
        "--region",
        action="store",
        dest="region",
        default=os.getenv("REGION", "us-central1"),
        type=str,
        help="""The region location of the k8s cluster. If not specified, uses REGION environment
            variable.""",
    )

    args = parser.parse_args()

    if args.providers == None:
        parser.print_help()
        sys.exit(1)

    if args.providers == "aws":
        if None in [args.cluster]:
            parser.print_help()
            sys.exit(1)

    if args.providers == "gcp":
        if None in [args.cluster, args.project]:
            parser.print_help()
            sys.exit(1)
    return args


def check_required_binaries(config):
    """
    Verify that the required binaries are present on the executing system.
    """
    binaries = True
    for binary in config.required_binaries:
        bin = subprocess.getoutput(f"which {binary}")
        if not bin:
            binaries = False
            logger.error(
                f"You are missing the binary {binary}, check the config file for a link to install the binary."
            )
    if not binaries:
        logger.error("Please install the missing binaries, then run addon_manager.py")
        sys.exit(1)


def update_kubeconfig(args):
    """
    Update the local kubeconfig so we can work with the k8s cluster.
    """
    if args.providers == "gcp":
        gcloud = subprocess.getoutput("which gcloud")
        run_command([gcloud, "config", "set", "project", args.project])
        run_command(
            [
                gcloud,
                "container",
                "clusters",
                "get-credentials",
                args.cluster,
                "--region",
                args.region,
            ]
        )

    if args.providers == "aws":
        aws = subprocess.getoutput("which aws")
        run_command(
            [
                aws,
                "eks",
                "update-kubeconfig",
                "--region",
                args.region,
                "--name",
                args.cluster,
                "--profile",
                args.environment,
            ]
        )


def main():
    args = arguments()

    with open(args.config) as f:
        config = objectify(YAML().load(f))
    addons_manager = Manager(args=args, config=config)
    update_kubeconfig(args)

    if args.action == "create":
        addons_manager.install(args.name)
    if args.action == "delete":
        addons_manager.delete(args.name)
    if args.action == "upgrade":
        addons_manager.upgrade(args.name)


if __name__ == "__main__":
    main()
