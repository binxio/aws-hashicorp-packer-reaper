import click
import durations

class Duration(click.ParamType):
    """
    A duration in human readable form as parsed by https://github.com/oleiade/durations
    """
    name = "duration"

    def convert(self, value, param, ctx) -> durations.Duration:
        if value is None:
            return value

        if isinstance(value, durations.Duration):
            return value

        try:
            return durations.Duration(value)
        except ValueError as e:
            self.fail(f'Could not parse "{value}" into duration ({e})', param, ctx)
