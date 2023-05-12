from argparse import ArgumentParser
import pkg.container as container

from pkg.service_manager_ex import ServiceManagerEx


class CommandHandler:
    __parser = None
    __parsed_args = None

    def __init__(self):
        type(self).__parser = ArgumentParser()

        subparser = type(self).__parser.add_subparsers(dest='command')

        install_parser = subparser.add_parser('setup')
        install_parser.add_argument('-f', '--force', action='store_true')
        install_parser.set_defaults(force=False)

        subparser.add_parser('init')
        subparser.add_parser('ls')
        subparser.add_parser('install')
        subparser.add_parser('start')
        subparser.add_parser('stop')

        require_parser = subparser.add_parser('require')
        require_parser.add_argument('service', nargs='+')

        require_parser = subparser.add_parser('remove')
        require_parser.add_argument('service', nargs=1)

        service_parser = subparser.add_parser('service')
        service_subparser = service_parser.add_subparsers(dest='service_command')
        service_subparser.add_parser('ls')
        service_subparser.add_parser('stop')
        service_subparser.add_parser('start')
        service_subparser.add_parser('restart')

        type(self).__parsed_args = type(self).__parser.parse_args()

    @staticmethod
    def get_parsed_args():
        return CommandHandler.__parsed_args

    @staticmethod
    def setup():
        container.setup(CommandHandler.__parsed_args.force)

    @staticmethod
    def install():
        ServiceManagerEx().install()

    @staticmethod
    def start():
        ServiceManagerEx().start()

    @staticmethod
    def stop():
        ServiceManagerEx().stop()

    @staticmethod
    def ls():
        ServiceManagerEx().ls()

    @staticmethod
    def require():
        ServiceManagerEx().require_services(CommandHandler.__parsed_args.service)

    @staticmethod
    def remove():
        ServiceManagerEx().remove_service(CommandHandler.__parsed_args.service)
