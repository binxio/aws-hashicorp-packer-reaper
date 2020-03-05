from pytz import UTC
from datetime import datetime, timedelta


class EC2Instance(dict):
    def __init__(self, i):
        self.update(i)

    @property
    def instance_id(self):
        return self["InstanceId"]

    @property
    def tags(self):
        return {t["Key"]: t["Value"] for t in self.get("Tags")}

    @property
    def name(self):
        return self.tags.get("Name", self.instance_id)

    @property
    def launch_time(self):
        return self.get("LaunchTime")

    @property
    def time_since_launch(self) -> timedelta:
        return UTC.localize(datetime.utcnow()) - self.launch_time

    @property
    def state(self):
        return self.get("State", {}).get("Name")

    def __str__(self):
        return f"{self.instance_id} ({self.name})"
