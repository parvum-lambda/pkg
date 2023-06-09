import subprocess
import os

PREFIX = '\x1B'
FORMATS = {
    '!R': '[0m',  # reset
    '!B': '[1m',  # bold
    '!U': '[4m',  # underlined
    '!r': '[31m',  # red
    '!c': '[32m',  # green
    '!y': '[33m',  # yellow
    '!b': '[34m',  # blue
    '!m': '[35m',  # magenta
    '!cy': '[36m'  # cyan
}


def formatex(_input):
    output = _input + '!R'
    for format_key in FORMATS:
        output = output.replace(format_key, PREFIX + FORMATS[format_key])

    return output


def run_read_sync(cmd, env_vars=None):
    env = os.environ.copy()

    if env_vars is not None:
        env.update(env_vars)

    try:
        return subprocess.check_output(['bash', '-c', cmd], env=env, stderr=subprocess.STDOUT).decode('utf8')
    except subprocess.CalledProcessError as e:
        print(formatex('!r' + e.output.decode() + '!R'))
        exit(1)
