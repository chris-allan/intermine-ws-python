import re

PATH_PATTERN = re.compile("^(?:\w+\.)*\w+$")

class PathFeature(object):
    def __init__(self, path):
        if not PATH_PATTERN.match(path):
            raise TypeError("Path does not match expected pattern" + re)
        self.path = path
    def __repr__(self):
        return "<" + self.__class__.__name__ + ": " + self.to_string() + ">"
    def to_string(self):
        return str(self.path)
    def to_dict(self):
        return { 'path' : self.path }
    @property
    def child_type(self):
        raise AttributeError()

class Join(PathFeature):
    valid_join_styles = ['OUTER', 'INNER']
    child_type = 'join'
    def __init__(self, path, style='OUTER'):
        if not style.uc in valid_join_styles:
            raise TypeError("Unknown join style: " + style)
        self.style = style
        super(Join, self).__init__(path)
    def to_dict(self):
        d = super(Join, self).to_dict()
        d.update(style=self.style)
        return d

class PathDescription(PathFeature):
    child_type = 'pathDescription'
    def __init__(self, path, description):
        self.description = description
        super(PathDescription, self).__init__(path)
    def to_dict(self):
        d = super(PathDescription, self).to_dict()
        d.update(description=self.description)
        return d

