from intermine.model import Reference

class PathError(Exception):
    pass

def get_subclass(key, model, subclass_dict, path):
    subclass = subclass_dict[key]
    current_class = model.class_by_name(subclass)
    if current_class is None:
        raise PathError(
            "%s not valid: %s is subclassed to %s, but could not find %s in model"
             % (path, key, subclass, subclass))
    else:
        return current_class

def verify(path, model, subclass_dict={}):
    descriptors = []
    names = path.split('.')
    root_name = names.pop(0)

    root_descriptor = model.class_by_name(root_name)
    if root_descriptor is None:
        raise PathError("%s not valid: Could not find root class %s in model"
                % (path, root_name))
    else:
        descriptors.append(root_descriptor)

    if root_name in subclass_dict:
        current_class = get_subclass(root_name, model, subclass_dict, path)
    else:
        current_class = root_descriptor 

    for field_name in names:
        try:
            field_descriptor = current_class.field_called[field_name]
        except KeyError:
            raise PathError("%s not valid: No field called %s in %s" 
                    % (path, field_name, current_class.name))
        except AttributeError:
            raise PathError("%s not valid: %s is not a class or a reference to a class"
                    % (path, descriptors[-1].name))
        descriptors.append(field_descriptor)

        if isinstance(field_descriptor, Reference):
            key = '.'.join(map(lambda x: x.name, descriptors))
            if key in subclass_dict:
                current_class = get_subclass(key, model, subclass_dict, path)
            else: 
                current_class = field_descriptor.type_class
        else:
            current_class = None

    return descriptors 


    
