import weakref
import urllib


class List(object):
    """
    Class for representing a List on an InterMine Webservice
    ========================================================

    Lists represent stored collections of data and saved result
    sets in an InterMine data warehouse. This class is an abstraction
    of this information, and provides mechanisms for managing the
    data.

    SYNOPSIS
    --------

    example::
        
        from intermine.webservice import Service

        flymine = Service("www.flymine.org/query", "SOMETOKEN")
        new_list = flymine.create_list(["h", "zen", "eve", "bib"], "Gene", name="My New List")

        another_list = flymine.get_list("Some other list")
        combined_list = new_list | another_list # Same syntax as for sets
        combined_list.name = "Union of the other lists"

        for row in combined_list.to_attribute_query().results():
            print row

    OVERVIEW
    --------

    Lists are created from a webservice, and can be manipulated in various ways. 
    The operations are:
        * Union: this | that
        * Intersection: this & that
        * Symmetric Difference: this ^ that
        * Asymmetric Difference (subtraction): this - that
        * Appending: this += that

    Lists can be created from a list of identifiers that could be:
        * stored in a file
        * held in a list or set
        * contained in a string
    In all these cases the syntax is the same:

        new_list = service.create_list(content, type, name="Some name", description="Some description", tags=["some", "tags"])

    Lists can also be created from a query's result with the exact 
    same syntax. In the case of queries, the type is not required,
    but the query should have just one view, and it should be an id.

        query = service.new_query()
        query.add_view("Gene.id")
        query.add_constraint("Gene.length", "<", 100)
        new_list = service.create_list(query, name="Short Genes")

    """

    def __init__(self, **args):
        """
        Constructor
        ===========

        Do not construct these objects yourself. They should be 
        fetched from a service or constructed using the "create_list"
        method.
        """
        try: 
            self.service = args["service"]
            self.manager = weakref.proxy(args["manager"])
            self._name = args["name"]
            self.title = args["title"]
            self.description = args.get("description")
            self.list_type = args["type"]
            self.size = int(args["size"])
            self.date_created = args.get("dateCreated")
            self.is_authorized = args.get("authorized")
            if self.is_authorized is None:
                self.is_authorized = True
            tags = args["tags"] if "tags" in args else []
            self.tags = frozenset(tags)
        except KeyError:
            raise ValueError("Missing argument") 
        self.unmatched_identifiers = set([])

    def get_name(self):
        return self._name

    def set_name(self, new_name):
        """
        Set the name of the list
        ========================

        Setting the list's name causes the list's name to be updated on the server.
        """
        if self._name == new_name:
            return
        uri = self.service.root + self.service.LIST_RENAME_PATH
        params = {
            "oldname": self._name,
            "newname": new_name
        }
        uri += "?" + urllib.urlencode(params)
        resp = self.service.opener.open(uri)
        data = resp.read()
        resp.close()
        new_list = self.manager.parse_list_upload_response(data)
        self._name = new_name

    def del_name(self):
        raise AttributeError("List names cannot be deleted, only changed")

    name = property(get_name, set_name, del_name, "The name of this list")

    def _add_failed_matches(self, ids):
        if ids is not None:
            self.unmatched_identifiers.update(ids)

    def __str__(self):
        string = self.name + " (" + str(self.size) + " " + self.list_type + ")"
        if self.date_created:
            string += " " + self.date_created
        if self.description:
            string += " " + self.description
        return string

    def delete(self):
        """
        Delete this list from the webservice
        ====================================

        Calls the webservice to delete this list immediately. This
        object should not be used after this method is called - attempts
        to do so will raise errors.
        """
        self.manager.delete_lists([self])

    def to_query(self):
        """
        Construct a query to fetch the items in this list
        =================================================

        Return a new query constrained to the objects in this list, 
        and with a single view column of the objects ids.

        @rtype: intermine.query.Query
        """
        q = self.service.new_query()
        q.add_view(self.list_type + ".id")
        q.add_constraint(self.list_type, "IN", self.name)
        return q

    def to_attribute_query(self):
        """
        Construct a query to fetch information about the items in this list
        ===================================================================

        Return a query constrained to contain the objects in this list, with 
        all the attributes of these objects selected for output as view columns
        
        @rtype: intermine.query.Query
        """
        q = self.to_query()
        attributes = q.model.get_class(self.list_type).attributes
        q.clear_view()
        q.add_view(map(lambda x: self.list_type + "." + x.name, attributes))
        return q

    def __and__(self, other):
        """
        Intersect this list and another
        """
        return self.manager.intersect([self, other])

    def __iand__(self, other):
        """
        Intersect this list and another, and replace this list with the result of the
        intersection
        """
        intersection = self.manager.intersect([self, other], description=self.description, tags=self.tags)
        self.delete()
        intersection.name = self.name
        return intersection

    def __or__(self, other):
        """ 
        Return the union of this list and another
        """
        return self.manager.union([self, other])

    def __add__(self, other):
        """ 
        Return the union of this list and another
        """
        return self.manager.union([self, other])

    def __iadd__(self, other):
        """ 
        Append other to this list.
        """
        return self.append(other)

    def _do_append(self, content):
        name = self.name
        data = None

        try:
            ids = open(content).read()
        except (TypeError, IOError):
            if isinstance(content, basestring):
                ids = content
            else:
                try:
                    ids = "\n".join(map(lambda x: '"' + x + '"', iter(content)))
                except TypeError:
                    try:
                        uri = content.get_list_append_uri()
                    except:
                        content = content.to_query()
                        uri = content.get_list_append_uri()
                    params = content.to_query_params()
                    params["listName"] = name
                    params["path"] = None
                    form = urllib.urlencode(params)
                    resp = self.service.opener.open(uri, form)
                    data = resp.read()

        if data is None:
            uri = self.service.root + self.service.LIST_APPENDING_PATH
            query_form = {'name': name}
            uri += "?" + urllib.urlencode(query_form)
            data = self.service.opener.post_plain_text(uri, ids)

        new_list = self.manager.parse_list_upload_response(data)
        self.unmatched_identifiers.update(new_list.unmatched_identifiers)
        self.size = new_list.size
        return self

    def append(self, appendix):
        "Append the arguments to this list"
        try:
            return self._do_append(self.manager.union(appendix))
        except:
            return self._do_append(appendix)

    def __xor__(self, other):
        """Calculate the symmetric difference of this list and another"""
        return self.manager.xor([self, other])

    def __ixor__(self, other):
        """Calculate the symmetric difference of this list and another and replace this list with the result"""
        diff = self.manager.xor([self, other], description=self.description, tags=self.tags)
        self.delete()
        diff.name = self.name
        return diff

    def __sub__(self, other):
        """Subtract the other from this list"""
        return self.manager.subtract([self], [other])

    def __isub__(self, other):
        """Replace this list with the subtraction of the other from this list"""
        subtr = self.manager.subtract([self], [other], description=self.description, tags=self.tags)
        self.delete()
        subtr.name = self.name
        return subtr

