from command_handler import CommandHandler

command_handler = CommandHandler()
parsed_args = command_handler.get_parsed_args()


def parse_command():
    return parsed_args.command.replace('-', '_')


command = getattr(CommandHandler, parse_command())
command()
