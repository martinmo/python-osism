import subprocess

from cliff.command import Command


class Run(Command):
    def get_parser(self, prog_name):
        parser = super(Run, self).get_parser(prog_name)
        parser.add_argument(
            "--type",
            default="ssh",
            choices=["ansible", "container", "ssh"],
            help="Type of the console (default: %(default)s)",
        )
        parser.add_argument(
            "host",
            nargs=1,
            type=str,
            help="Hostname or address of the console to connect",
        )
        return parser

    def take_action(self, parsed_args):
        type_console = parsed_args.type
        host = parsed_args.host[0]

        # If certain characters are contained in the hostname, then
        # enforce a certain console type.

        # ctl001/rabbitmq
        if "/" in host:
            type_console = "container"
        # .ctl001
        elif host.startswith("."):
            type_console = "ansible"
            host = host[1:]

        if type_console == "ansible":
            subprocess.call(f"/run-ansible-console.sh {host}", shell=True)
        elif type_console == "ssh":
            # FIXME: use paramiko or something else more Pythonic + make operator user + key configurable
            subprocess.call(
                f"/usr/bin/ssh -i /ansible/secrets/id_rsa.operator -o StrictHostKeyChecking=no -o LogLevel=ERROR dragon@{host}",
                shell=True,
            )
        elif type_console == "container":
            target_containername = host.split("/")[1]
            target_host = host.split("/")[0]
            target_command = "bash"

            ssh_command = f"docker exec -it {target_containername} {target_command}"
            ssh_options = (
                "-o RequestTTY=force -o StrictHostKeyChecking=no -o LogLevel=ERROR"
            )

            # FIXME: use paramiko or something else more Pythonic + make operator user + key configurable
            subprocess.call(
                f"/usr/bin/ssh -i /ansible/secrets/id_rsa.operator {ssh_options} dragon@{target_host} {ssh_command}",
                shell=True,
            )
