import re

PATTERN_STR = "^(?:\w+\.)*\w+$"
PATH_PATTERN = re.compile(PATTERN_STR)

class PathFeature(object):
    def __init__(self, path):
        if not PATH_PATTERN.match(path):
            raise TypeError(
                "Path '" + path + "' does not match expected pattern" + PATTERN_STR)
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
    INNER = "INNER"
    OUTER = "OUTER"
    child_type = 'join'
    def __init__(self, path, style='OUTER'):
        if style.upper() not in Join.valid_join_styles:
            raise TypeError("Unknown join style: " + style)
        self.style = style.upper()
        super(Join, self).__init__(path)
    def to_dict(self):
        d = super(Join, self).to_dict()
        d.update(style=self.style)
        return d
    def __repr__(self):
        return('<' + self.__class__.__name__ 
                + ' '.join([':', self.path, self.style]) + '>')

class PathDescription(PathFeature):
    child_type = 'pathDescription'
    def __init__(self, path, description):
        self.description = description
        super(PathDescription, self).__init__(path)
    def to_dict(self):
        d = super(PathDescription, self).to_dict()
        d.update(description=self.description)
        return d

