import subprocess

from .utils import run_command


class BaseManager(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.post_init()

    def install(self):
        raise NotImplementedError

    def post_init(self):
        return


def helm(
    action,
    namespace=None,
    release=None,
    chart=None,
    values=None,
    version=None,
    license_file=None,
    noout=None,
):
    """
    Pass through method to execute a helm command.
    """
    command = [subprocess.getoutput("which helm")]
    if namespace:
        command.append("--namespace")
        command.append(namespace)
    if " " in action:
        args = action.split(" ")
        for arg in args:
            command.append(arg)
    else:
        command.append(action)
    if action == "upgrade":
        # adds a switch so if a release by this name doesn't already exist, install the release
        command.append("--install")
    if release:
        command.append(release)
    if chart:
        command.append(chart)
    if license_file:
        command.append("--set-file")
        command.append(f"license={license_file}")
    if values:
        command.append("--values")
        command.append(values)
    if version:
        command.append("--version")
        command.append(version)
    run_command(command, noout)


def kubectl(action, namespace=None, resource=None, filename=None, literal=None):
    """
    Pass through method to exectue a kubectl command.
    """
    command = [subprocess.getoutput("which kubectl")]
    if namespace:
        command.append("--namespace")
        command.append(namespace)
    if " " in action:
        args = action.split(" ")
        for arg in args:
            command.append(arg)
    else:
        command.append(action)

    if resource:
        if " " in resource:
            args = resource.split(" ")
            for arg in args:
                command.append(arg)
        else:
            command.append(resource)
        run_command(command)
        return
    if filename:
        command.append("-f")
        command.append(filename)
        run_command(command)
        return
    if literal:
        command.append("--from-literal")
        command.append(literal)
        run_command(command)
