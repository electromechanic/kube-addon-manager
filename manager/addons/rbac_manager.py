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
        Delete RBAC Manager.
        """
        if "dev" in self.args.cluster:
            self.rbac_dev_binder(action="delete")
        self.rbac_oncall_binder(action="delete")
        self.metrics_role(action="delete")
        self.nodes_clusterrole(action="delete")
        self.oncall_role(action="delete")
        self.priorityclass_clusterrole(action="delete")
        self.priorityclasses(action="delete")
        self.rbac_manager(action="delete")

    def install(self):
        """
        Logic for the installation of RBAC Manager.
        """
        self.rbac_manager(action="upgrade")
        self.metrics_role(action="apply")
        self.nodes_clusterrole(action="apply")
        self.oncall_role(action="apply")
        self.priorityclass_clusterrole(action="apply")
        self.priorityclasses(action="apply")
        self.rbac_oncall_binder(action="apply")
        if "dev" in self.args.cluster:
            self.rbac_dev_binder(action="apply")

    def metrics_role(self, action="apply"):
        """
        Manage the clusterrole to add in mtrics api.
        """
        role = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {
                "name": "system:aggregated-metrics-reader",
                "labels": {
                    "rbac.authorization.k8s.io/aggregate-to-view": "true",
                    "rbac.authorization.k8s.io/aggregate-to-edit": "true",
                    "rbac.authorization.k8s.io/aggregate-to-admin": "true",
                },
            },
            "rules": [
                {
                    "apiGroups": ["metrics.k8s.io"],
                    "resources": ["pods", "nodes"],
                    "verbs": ["get", "list", "watch"],
                }
            ],
        }

        with open("role.yaml", "w") as f:
            YAML().dump(role, f)

        kubectl(action=action, filename="role.yaml")
        os.unlink("role.yaml")

    def nodes_clusterrole(self, action="apply"):
        """
        Manage the clusterrole to add in nodes objects api.
        """
        role = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {
                "name": "nodes-reader",
                "labels": {
                    "rbac.authorization.k8s.io/aggregate-to-view": "true",
                    "rbac.authorization.k8s.io/aggregate-to-edit": "true",
                    "rbac.authorization.k8s.io/aggregate-to-admin": "true",
                },
            },
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["nodes"],
                    "verbs": ["get", "list", "watch"],
                }
            ],
        }

        with open("role.yaml", "w") as f:
            YAML().dump(role, f)

        kubectl(action=action, filename="role.yaml")
        os.unlink("role.yaml")

    def oncall_role(self, action="apply"):
        """
        Manage the oncall role for prod clusters.
        """
        role = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {
                "name": "oncall-role",
            },
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["pods"],
                    "verbs": ["get", "watch", "list", "describe", "delete"],
                },
                {"apiGroups": [""], "resources": ["events"], "verbs": ["get", "list"]},
                {"apiGroups": [""], "resources": ["pods/log"], "verbs": ["get"]},
                {"apiGroups": [""], "resources": ["pods/portforward"], "verbs": ["create"]},
                {
                    "apiGroups": ["", "extensions"],
                    "resources": ["deployments"],
                    "verbs": ["get", "watch", "list", "describe"],
                },
                {
                    "apiGroups": [""],
                    "resources": ["services"],
                    "verbs": ["get", "watch", "list", "describe"],
                },
                {
                    "apiGroups": ["", "batch"],
                    "resources": ["jobs"],
                    "verbs": ["get", "watch", "list", "describe", "delete"],
                },
                {
                    "apiGroups": ["", "batch"],
                    "resources": ["cronjobs"],
                    "verbs": ["get", "watch", "list", "describe", "edit"],
                },
            ],
        }
        with open("role.yaml", "w") as f:
            YAML().dump(role, f)

        kubectl(action=action, filename="role.yaml")
        os.unlink("role.yaml")

    def priorityclass_clusterrole(self, action="apply"):
        """
        Manage the clusterrole to add in priorityclass objects api.
        """
        role = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {
                "name": "priorityclass-reader",
                "labels": {
                    "rbac.authorization.k8s.io/aggregate-to-view": "true",
                    "rbac.authorization.k8s.io/aggregate-to-edit": "true",
                    "rbac.authorization.k8s.io/aggregate-to-admin": "true",
                },
            },
            "rules": [
                {
                    "apiGroups": ["scheduling.k8s.io"],
                    "resources": ["priorityclasses"],
                    "verbs": ["get", "list", "watch"],
                }
            ],
        }

        with open("role.yaml", "w") as f:
            YAML().dump(role, f)

        kubectl(action=action, filename="role.yaml")
        os.unlink("role.yaml")

    def _priorityclass_render(self, pc, action):
        """
        Helper method to handle the render and applcation of the priorityclass
        """
        priorityclass = {
            "apiVersion": "scheduling.k8s.io/v1",
            "kind": "PriorityClass",
            "metadata": {
                "name": pc.name,
            },
            "value": pc.value,
            "preemptionPolicy": pc.preemptionPolicy,
        }
        if "labels" in pc.keys():
            priorityclass["metadata"]["labels"] = pc.labels.to_dict()
        if "globalDefault" in pc.keys():
            priorityclass["globalDefault"] = pc.globalDefault
        if "description" in pc.keys():
            priorityclass["description"] = pc.description

        with open("priorityclass.yaml", "w") as f:
            YAML().dump(priorityclass, f)

        kubectl(action=action, filename="priorityclass.yaml")
        os.unlink("priorityclass.yaml")

    def priorityclasses(self, action="apply"):
        """
        Manage the priorityclasses from config.
        """
        for pc in self.config.priorityclasses.all:
            self._priorityclass_render(pc, action)
        for pc in self.config.priorityclasses.dev:
            if "dev" in self.args.cluster:
                self._priorityclass_render(pc, action)
        for pc in self.config.priorityclasses.prod:
            if "prod" in self.args.cluster:
                self._priorityclass_render(pc, action)

    def rbac_dev_binder(self, action="apply"):
        """
        Manage bindings for the dev teams in dev clusters.
        """
        groups = [
            "core-engine",
            "machine-learning",
            "product-engineering-ind",
            "product-engineering-usa",
            "solutions-architecture",
        ]

        binder = {
            "apiVersion": "rbacmanager.reactiveops.io/v1beta1",
            "kind": "RBACDefinition",
            "metadata": {"name": "dev-access"},
            "rbacBindings": [],
        }

        for group in groups:
            binder["rbacBindings"].append(
                {
                    "name": group,
                    "subjects": [{"kind": "Group", "name": group}],
                    "clusterRoleBindings": [
                        {
                            "clusterRole": "edit",
                        },
                        {"clusterRole": "system:aggregate-to-edit"},
                    ],
                }
            )

        with open("binder.yaml", "w") as f:
            YAML().dump(binder, f)

        kubectl(action=action, filename="binder.yaml")
        os.unlink("binder.yaml")

    def rbac_oncall_binder(self, action="apply"):
        """
        Manage the rbac definitiona that will bind permissions based on namespace labels.
        """
        binder = {
            "apiVersion": "rbacmanager.reactiveops.io/v1beta1",
            "kind": "RBACDefinition",
            "metadata": {"name": "oncall-access"},
            "rbacBindings": [
                {
                    "name": "oncall",
                    "subjects": [{"kind": "Group", "name": "oncall"}],
                    "roleBindings": [
                        {
                            "clusterRole": "oncall-role",
                            "namespaceSelector": {"matchLabels": {"oncall": "true"}},
                        }
                    ],
                }
            ],
        }
        with open("binder.yaml", "w") as f:
            YAML().dump(binder, f)

        kubectl(action=action, filename="binder.yaml")
        os.unlink("binder.yaml")

    def rbac_manager(self, action="upgrade"):
        """
        Install RBAC Manager.
        """
        values = {
            "nodeSelector": {"nodegroup": "addons"},
        }
        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "rbac-manager",
            "release": "rbac-manager",
        }
        if action != "delete":
            params["chart"] = "fairwinds-stable/rbac-manager"
            if self.args.providers == "gcp":
                params["values"] = "values.yaml"
                logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def upgrade(self):
        """
        Logic for the upgrade of RBAC Manager.
        """
        self.rbac_manager(action="upgrade")
        self.metrics_role(action="apply")
        self.nodes_clusterrole(action="apply")
        self.oncall_role(action="apply")
        self.priorityclass_clusterrole(action="apply")
        self.priorityclasses(action="apply")
        self.rbac_oncall_binder(action="apply")
        if "dev" in self.args.cluster:
            self.rbac_dev_binder(action="apply")
