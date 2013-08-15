from xblock.core import Scope
from xmodule.x_module import XModuleDescriptor
from xblock.runtime import KeyValueStore

# A list of metadata that this module can inherit from its parent module
INHERITABLE_METADATA = (
    'graded', 'start', 'due', 'graceperiod', 'showanswer', 'rerandomize',
    # TODO (ichuang): used for Fall 2012 xqa server access
    'xqa_key',
    # How many days early to show a course element to beta testers (float)
    # intended to be set per-course, but can be overridden in for specific
    # elements.  Can be a float.
    'days_early_for_beta',
    'giturl'  # for git edit link
)


def compute_inherited_metadata(descriptor):
    """Given a descriptor, traverse all of its descendants and do metadata
    inheritance.  Should be called on a CourseDescriptor after importing a
    course.

    NOTE: This means that there is no such thing as lazy loading at the
    moment--this accesses all the children."""
    # compute the values to be inherited by the children
    parent_metadata = descriptor.xblock_kvs.inherited_settings.copy()
    if descriptor.has_children:
        # add any of descriptor's explicitly set fields to the inheriting list
        for field in INHERITABLE_METADATA:
            # pylint: disable = W0212
            if field in descriptor._model_data:
                parent_metadata[field] = descriptor._model_data[field]

        for child in descriptor.get_children():
            inherit_metadata(child, parent_metadata)
            compute_inherited_metadata(child)


def inherit_metadata(descriptor, inheriting_metadata):
    """
    Updates this module with metadata inherited from a containing module.
    Only metadata specified in self.inheritable_metadata will
    be inherited
    """
    descriptor.xblock_kvs.inherited_settings = inheriting_metadata


def own_metadata(module):
    """
    Return a dictionary that contains only non-inherited field keys,
    mapped to their values
    """
    return module.get_explicitly_set_fields_by_scope(Scope.settings)

class InheritanceKeyValueStore(KeyValueStore):
    """
    Common superclass for kvs's which know about inheritance of settings. Offers simple
    dict-based storage of fields and lookup of inherited values.
    """
    def __init__(self, initial_values=None, inherited_settings=None):
        super(InheritanceKeyValueStore, self).__init__()
        self._inherited_settings = inherited_settings or {}
        self._fields = initial_values or {}

    @property
    def inherited_settings(self):
        """
        Get the settings set by the ancestors (which locally set fields may override or not)
        """
        return self._inherited_settings

    @inherited_settings.setter
    def inherited_settings(self, dictvalue):
        self._inherited_settings = dictvalue

    def get(self, key):
        if key.field_name in self._fields:
            return self._fields[key.field_name]
        elif key.field_name in self.inherited_settings:
            return self.inherited_settings[key.field_name]
        else:
            raise KeyError()

    def set(self, key, value):
        # xml backed courses are read-only, but they do have some computed fields
        self._fields[key.field_name] = value

    def delete(self, key):
        del self._fields[key.field_name]

    def has(self, key):
        return key.field_name in self._fields

