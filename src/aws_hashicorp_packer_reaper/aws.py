import pytz
from typing import Optional, Tuple
from datetime import datetime, timedelta


class Tag(object):
    """
    a key value pair.

    >>> Tag("Name")
    Name
    >>> Tag("Name", "Value")
    Name=Value
    """

    def __init__(self, key: str, value: Optional[str] = None):
        super(Tag, self).__init__()
        self.key = key
        self.value = value

    @staticmethod
    def from_string(s: str):
        """
        Creates a tag from a string representation.

        >>> Tag.from_string("Name=Value")
        Name=Value
        >>> Tag.from_string("Name")
        Name
        >>> Tag.from_string("Name=ab=c").value
        'ab=c'
        """
        splits = s.split("=", 1)
        return Tag(key=splits[0], value=None if len(splits) == 1 else splits[1])

    def __repr__(self) -> str:
        return f"{self.key}={self.value}" if self.value else self.key


class TagFilter(object):
    """
    A boto3 tag filter

    >>> TagFilter([Tag("Name")])
    [{'Name': 'tag:Name', 'Values': []}]

    >>> TagFilter([Tag("Name", "Value")])
    [{'Name': 'tag:Name', 'Values': ['Value']}]

    >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value2")])
    [{'Name': 'tag:Name', 'Values': ['Value', 'Value2']}]

    >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value")])
    [{'Name': 'tag:Name', 'Values': ['Value']}]

    >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value2"), Tag("Region", "eu-west-1a"), Tag("Region", "eu-west-1b")])
    [{'Name': 'tag:Name', 'Values': ['Value', 'Value2']}, {'Name': 'tag:Region', 'Values': ['eu-west-1a', 'eu-west-1b']}]
    """

    def __init__(self, tags: Tuple[Tag]):
        self.filter = {}
        for tag in tags:
            key = f"tag:{tag.key}"
            if not self.filter.get(key):
                self.filter[key] = []
            if tag.value:
                if tag.value not in self.filter[key]:
                    self.filter[key].append(tag.value)

    def to_api(self):
        """
        returns an array of dictionaries with `Name` and `Values` set as expected by the boto3 api.

        >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value2")]).to_api()
        [{'Name': 'tag:Name', 'Values': ['Value', 'Value2']}]

        """
        return [{"Name": f"{k}", "Values": self.filter[k]} for k in self.filter.keys()]

    def __repr__(self):
        return str(self.to_api())


class ReaperTagFilter(TagFilter):
    """
    A reaper tag filter, which has a fixed filter for the tag:Name `Packer Builder`.

    >>> ReaperTagFilter()
    [{'Name': 'tag:Name', 'Values': ['Packer Builder']}]
    """

    def __init__(self, tags: Tuple[Tag] = []):
        super(ReaperTagFilter, self).__init__(tags)
        self.filter["tag:Name"] = ["Packer Builder"]


class EC2Instance(dict):
    """
    EC2 instances are returned by the boto api.

    """

    def __init__(self, i):
        super(EC2Instance, self).__init__()
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
        return pytz.utc.localize(dt=datetime.utcnow()) - self.launch_time

    @property
    def state(self):
        return self.get("State", {}).get("Name")

    def __str__(self):
        return f"{self.instance_id} ({self.name})"
