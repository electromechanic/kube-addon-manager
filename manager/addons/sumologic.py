import logging
import os

from manager import BaseManager, helm, utils
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


class Manager(BaseManager):
    def post_init(self):
        self.args = self.kwargs.get("args")
        self.config = self.kwargs.get("config")
        self.provider = self.args.providers

    def delete(self):
        """
        Delete the sumologic addon.
        """
        self.sumologic(action="delete")

    def install(self):
        """
        Logic for the installation of sumoligc.
        """
        self.sumologic(action="install")

    def sumologic(self, action="upgrade"):
        """
        Handle the values file.
        """
        namespace_selector = "sisu"
        if self.args.cluster == "prod-cluster":
            namespace_selector = "prod"

        values = {
            "sumologic": {
                "accessId": os.getenv("SUMO_ACCESS_ID"),
                "accessKey": os.getenv("SUMO_ACCESS_KEY"),
                "collectorName": self.args.cluster,
                "clusterName": self.args.cluster,
                "collectionMonitoring": False,
                "traces": {"enabled": True},
                "metrics": {
                    "otelcol": {
                        "extraProcessors": [
                            {
                                "filter/exclude_sumo_metrics": {
                                    "metrics": {
                                        "exclude": {
                                            "match_type": "strict",
                                            "resource_attributes": [
                                                {"key": "k8s.namespace.name", "value": "sumologic"},
                                                # regexp not working with namespace targetting, issue being worked by sumo
                                                # {"key": "k8s.namespace.name", "value": "hotfix.*"},
                                                # {"key": "k8s.namespace.name", "value": "master.*"},
                                                # {"key": "k8s.namespace.name", "value": "pr.*"},
                                                # {
                                                #    "key": "k8s.namespace.name",
                                                #    "value": "rollback-e2e.*",
                                                # },
                                            ],
                                        }
                                    }
                                }
                            }
                        ]
                    }
                },
            },
            "kube-prometheus-stack": {
                "kubeApiServer": {"serviceMonitor": {"interval": "5m"}},
                "kubeControllerManager": {"serviceMonitor": {"interval": "5m"}},
                "kubeEtcd": {"serviceMonitor": {"interval": "5m"}},
                "KubeScheduler": {"serviceMonitor": {"interval": "5m"}},
                "prometheus": {
                    "additionalServiceMonitors": [
                        {
                            "name": "backend",
                            "additionalLabels": {"app": "backend"},
                            "endpoints": [
                                {
                                    "port": "metrics",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                },
                                {
                                    "port": "ingest-sidecar-metrics",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                },
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "backend"}},
                        },
                        {
                            "name": "workflow-manager",
                            "additionalLabels": {"app": "workflow-manager"},
                            "endpoints": [
                                {
                                    "port": "meta-port",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                }
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "workflow-manager"}},
                        },
                        {
                            "name": "workflow-runner",
                            "additionalLabels": {"app": "workflow-runner"},
                            "endpoints": [
                                {
                                    "port": "targetPort",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                }
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "workflow-runner"}},
                        },
                        {
                            "name": "asset-generator",
                            "additionalLabels": {"app": "asset-generator"},
                            "endpoints": [
                                {
                                    "port": "meta-port",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                }
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "asset-generator"}},
                        },
                        {
                            "name": "api",
                            "additionalLabels": {"app": "api"},
                            "endpoints": [
                                {
                                    "port": "meta-port",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                }
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "api"}},
                        },
                        {
                            "name": "uwsgi-exporter",
                            "additionalLabels": {"app": "uwsgi-exporter"},
                            "endpoints": [
                                {
                                    "port": "http",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                }
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "uwsgi-exporter"}},
                        },
                        {
                            "name": "webapp",
                            "additionalLabels": {"app": "webapp"},
                            "endpoints": [
                                {
                                    "port": "web",
                                    "path": "/internal/prometheus_metrics",
                                    "relabelings": [
                                        {
                                            "sourceLabels": ["__name__"],
                                            "separator": ";",
                                            "regex": "(.*)",
                                            "targetLabel": "_sumo_forward_",
                                            "replacement": "true",
                                            "action": "replace",
                                        }
                                    ],
                                },
                            ],
                            "namespaceSelector": {"matchNames": [namespace_selector]},
                            "selector": {"matchLabels": {"app": "webapp"}},
                        },
                    ]
                },
            },
            "metadata": {
                "metrics": {
                    "autoscaling": {
                        "enabled": True,
                        "minReplicas": 3,
                        "maxReplicas": 10,
                        "targetCPUUtilizationPercentage": 80,
                    }
                },
                "logs": {
                    "autoscaling": {
                        "enabled": True,
                        "minReplicas": 3,
                        "maxReplicas": 10,
                        "targetCPUUtilizationPercentage": 80,
                    }
                },
            },
            "otelagent": {"daemonset": {"tolerations": [{"operator": "Exists"}]}},
            "otellogs": {
                "daemonset": {
                    "tolerations": [{"effect": "NoSchedule", "operator": "Exists"}],
                }
            },
        }

        if self.provider == "aws":
            values["otellogs"]["daemonset"]["affinity"] = {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "eks.amazonaws.com/compute-type",
                                        "operator": "NotIn",
                                        "values": ["fargate"],
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
            values["kube-prometheus-stack"]["prometheus-node-exporter"] = {
                "affinity": {
                    "nodeAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": {
                            "nodeSelectorTerms": [
                                {
                                    "matchExpressions": [
                                        {
                                            "key": "eks.amazonaws.com/compute-type",
                                            "operator": "NotIn",
                                            "values": ["fargate"],
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            }

        if self.provider == "gcp":
            values["sumologic"]["metrics"]["remoteWriteProxy"] = {
                "nodeSelector": {"nodegroup": "addons"}
            }
            values["sumologic"]["metrics"]["collector"] = {
                "otelcol": {"nodeSelector": {"nodegroup": "addons"}}
            }
            values["sumologic"]["setup"] = {"job": {"nodeSelector": {"nodegroup": "addons"}}}
            values["kube-prometheus-stack"]["kube-state-metrics"] = {
                "nodeSelector": {"nodegroup": "addons"}
            }
            values["kube-prometheus-stack"]["prometheus"]["prometheusSpec"] = {
                "nodeSelector": {"nodegroup": "addons"}
            }
            values["otelevents"] = {"statefulset": {"nodeSelector": {"nodegroup": "addons"}}}
            values["otelcolInstrumentation"] = {
                "statefulset": {"nodeSelector": {"nodegroup": "addons"}}
            }
            values["tracesGateway"] = {"deployment": {"nodeSelector": {"nodegroup": "addons"}}}
            values["tracesSampler"] = {"deployment": {"nodeSelector": {"nodegroup": "addons"}}}
            values["metadata"]["metrics"]["statefulset"] = {"nodeSelector": {"nodegroup": "addons"}}
            values["metadata"]["logs"]["statefulset"] = {"nodeSelector": {"nodegroup": "addons"}}
            values["pvcCleaner"] = {"job": {"nodeSelector": {"nodegroup": "addons"}}}

        with open("values.yaml", "w") as f:
            YAML().dump(values, f)

        params = {
            "action": action,
            "namespace": "sumologic",
            "release": f"sumologic",
        }
        if action != "delete":
            params["chart"] = "sumologic/sumologic"
            params["values"] = "values.yaml"
            params["version"] = self.config.version
            logger.info("Values for helm chart are:\n%s", utils.stringify_yaml(values))

        helm(**params)
        os.unlink("values.yaml")

    def upgrade(self):
        """
        Upgrade the chart installs.
        """
        self.sumologic(action="upgrade")
