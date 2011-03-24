import re
import string
from intermine.pathfeatures import PathFeature, PATH_PATTERN

class Constraint(PathFeature):
    child_type = "constraint"

class LogicNode(object):
    def __and__(self, other):
        if not isinstance(other, LogicNode):
            return NotImplemented
        else:
            return LogicGroup(self, 'and', other)
    def __or__(self, other):
        if not isinstance(other, LogicNode):
            return NotImplemented
        else:
            return LogicGroup(self, 'or', other)

class LogicGroup(LogicNode):
    LEGAL_OPS = set(['and', 'or'])
    def __init__(self, left, op, right):
        if not op in self.LEGAL_OPS:
            raise TypeError(op + " is not a legal logical operation")
        self.left = left
        self.right = right
        self.op = op
    def __str__(self):
        return ' '.join(map(str, [self.left, self.op, self.right]))

class CodedConstraint(Constraint, LogicNode):
    OPS = set([])
    def __init__(self, path, op):
        if op not in self.OPS:
            raise TypeError(op + " not in " + str(self.OPS))
        self.op = op
        self.code = 'A'
        super(CodedConstraint, self).__init__(path)
    def __str__(self):
        return self.code
    def to_string(self):
        s = super(CodedConstraint, self).to_string()
        return " ".join([s, self.op])
    def to_dict(self):
        d = super(CodedConstraint, self).to_dict()
        d.update(op=self.op, code=self.code)
        return d
    
class UnaryConstraint(CodedConstraint):
    OPS = set(['IS NULL', 'IS NOT NULL'])

class BinaryConstraint(CodedConstraint):
    OPS = set(['=', '!=', '<', '>', '<=', '>='])
    def __init__(self, path, op, value):
        self.value = value
        super(BinaryConstraint, self).__init__(path, op)

    def to_string(self):
        s = super(BinaryConstraint, self).to_string()
        return " ".join([s, str(self.value)])
    def to_dict(self):
        d = super(BinaryConstraint, self).to_dict()
        d.update(value=str(self.value))
        return d
    
class TernaryConstraint(BinaryConstraint):
    OPS = set(['LOOKUP'])
    def __init__(self, path, op, value, extra_value=None):
        self.extra_value = extra_value
        super(TernaryConstraint, self).__init__(path, op, value)

    def to_string(self):
        s = super(TernaryConstraint, self).to_string()
        if self.extra_value is None:
            return s
        else:
            return " ".join([s, 'IN', self.extra_value])
    def to_dict(self):
        d = super(TernaryConstraint, self).to_dict()
        if self.extra_value is not None:
            d.update(extraValue=self.extra_value)
        return d

class MultiConstraint(CodedConstraint):
    OPS = set(['ONE OF', 'NONE OF'])
    def __init__(self, path, op, values):
        if not isinstance(values, list):
            raise TypeError("values must be a list, not " + str(type(values)))
        self.values = values
        super(MultiConstraint, self).__init__(path, op)

    def to_string(self):
        s = super(MultiConstraint, self).to_string()
        return ' '.join([s, str(self.values)])
    def to_dict(self):
        d = super(MultiConstraint, self).to_dict()
        d.update(value=self.values)
        return d

class SubClassConstraint(Constraint):
    def __init__(self, path, subclass):
       if not PATH_PATTERN.match(subclass):
            raise TypeError
       self.subclass = subclass
       super(SubClassConstraint, self).__init__(path)
    def to_string(self):
       s = super(SubClassConstraint, self).to_string()
       return s + ' ISA ' + self.subclass
    def to_dict(self):
       d = super(SubClassConstraint, self).to_dict()
       d.update(type=self.subclass) 
       return d


class TemplateConstraint(object):
    REQUIRED = "required"
    OPTIONAL_ON = "on"
    OPTIONAL_OFF = "off"
    def __init__(self, editable=True, optional="required"):
        self.editable = editable
        if optional == TemplateConstraint.REQUIRED:
            self.optional = False
            self.switched_on = True
        else:
            self.optional = True
            if optional == TemplateConstraint.OPTIONAL_ON:
                self.switched_on = True
            elif optional == TemplateConstraint.OPTIONAL_OFF:
                self.switched_on = False
            else:
                raise TypeError("Bad value for optional")
    def get_switchable_status(self):
        if not self.optional:
            return "locked"
        else:
            switch = "on" if self.switched_on else "off"
            return switch

    def to_string(self):
        editable = "editable" if self.editable else "non-editable"
        return '(' + editable + ", " + self.get_switchable_status() + ')'

class TemplateUnaryConstraint(UnaryConstraint, TemplateConstraint):
    def __init__(self, *a, **d):
        UnaryConstraint.__init__(self, *a, **d)
    	for i in ["path", "op"]:
	        if i in d: del d[i]
        TemplateConstraint.__init__(self, **d)
    def to_string(self):
        return(UnaryConstraint.to_string(self) 
                + " " + TemplateConstraint.to_string(self))

class TemplateBinaryConstraint(BinaryConstraint, TemplateConstraint):
    def __init__(self, *a, **d):
        BinaryConstraint.__init__(self, *a, **d)
        for i in ["path", "op", "value"]:
            if i in d: del d[i]
        TemplateConstraint.__init__(self, **d)
    def to_string(self):
        return(BinaryConstraint.to_string(self) 
                + " " + TemplateConstraint.to_string(self))

class TemplateTernaryConstraint(TernaryConstraint, TemplateConstraint):
    def __init__(self, *a, **d):
        TernaryConstraint.__init__(self, *a, **d)
        for i in ["path", "op", "value"]:
            if i in d: del d[i]
        TemplateConstraint.__init__(self, **d)
    def to_string(self):
        return(TernaryConstraint.to_string(self) 
                + " " + TemplateConstraint.to_string(self))

class TemplateMultiConstraint(MultiConstraint, TemplateConstraint):
    def __init__(self, *a, **d):
        MultiConstraint.__init__(self, *a, **d)
        for i in ["path", "op", "values"]:
            if i in d: del d[i]
        TemplateConstraint.__init__(self, **d)
    def to_string(self):
        return(MultiConstraint.to_string(self) 
                + " " + TemplateConstraint.to_string(self))

class TemplateSubClassConstraint(SubClassConstraint, TemplateConstraint):
    def __init__(self, *a, **d):
        SubClassConstraint.__init__(self, *a, **d)
        for i in ["path", "subclass"]:
            if i in d: del d[i]
        TemplateConstraint.__init__(self, **d)
    def to_string(self):
        return(SubClassConstraint.to_string(self) 
                + " " + TemplateConstraint.to_string(self))

class ConstraintFactory(object):

    CONSTRAINT_CLASSES = set([
        UnaryConstraint, BinaryConstraint, TernaryConstraint, 
        MultiConstraint, SubClassConstraint])

    def __init__(self):
        self._codes = iter(string.ascii_uppercase)
    
    def get_next_code(self):
        return self._codes.next()

    def make_constraint(self, *args, **kwargs):
        for CC in self.CONSTRAINT_CLASSES:
            try:
                c = CC(*args, **kwargs)
                c.code = self.get_next_code()
                return c
            except TypeError:
                pass
        raise TypeError("No matching constraint class found for " 
            + str(args) + ", " + str(kwargs))
    
class TemplateConstraintFactory(ConstraintFactory):
    CONSTRAINT_CLASSES = set([
        TemplateUnaryConstraint, TemplateBinaryConstraint, 
        TemplateTernaryConstraint, TemplateMultiConstraint,
        TemplateSubClassConstraint,
    ])
