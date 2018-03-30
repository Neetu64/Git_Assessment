"""Clowder API

This module provides simple wrappers around the clowder Collections API
"""

from client import ClowderClient
from datasets import DatasetsApi


# TODO: Functions outside CollectionsApi are deprecated
def create_empty(connector, host, key, collectionname, description, parentid=None, spaceid=None):
    """Create a new collection in Clowder.

    Keyword arguments:
    connector -- connector information, used to get missing parameters and send status updates
    host -- the clowder host, including http and port, should end with a /
    key -- the secret key to login to clowder
    collectionname -- name of new dataset to create
    description -- description of new dataset
    parentid -- id of parent collection
    spaceid -- id of the space to add dataset to
    """

    client = CollectionsApi(host=host, key=key)
    return client.create(collectionname, description, parentid, spaceid)

def delete(connector, host, key, collectionid):

    client = CollectionsApi(host=host, key=key)
    return client.delete(collectionid)

def get_child_collections(connector, host, key, collectionid):
    """Get list of child collections in collection by UUID.

    Keyword arguments:
    connector -- connector information, used to get missing parameters and send status updates
    host -- the clowder host, including http and port, should end with a /
    key -- the secret key to login to clowder
    collectionid -- the collection to get children of
    """

    client = CollectionsApi(host=host, key=key)
    return client.get_child_collections(collectionid)

def get_datasets(connector, host, key, collectionid):
    """Get list of datasets in collection by UUID.

    Keyword arguments:
    connector -- connector information, used to get missing parameters and send status updates
    host -- the clowder host, including http and port, should end with a /
    key -- the secret key to login to clowder
    datasetid -- the collection to get datasets of
    """

    client = CollectionsApi(host=host, key=key)
    return client.get_datasets(collectionid)

# pylint: disable=too-many-arguments
def upload_preview(connector, host, key, collectionid, previewfile, previewmetadata):
    """Upload preview to Clowder.

    Keyword arguments:
    connector -- connector information, used to get missing parameters and send status updates
    host -- the clowder host, including http and port, should end with a /
    key -- the secret key to login to clowder
    collectionid -- the file that is currently being processed
    preview -- the file containing the preview
    previewdata: any metadata to be associated with preview,
                    this can contain a section_id to indicate the
                    section this preview should be associated with.
    """

    client = CollectionsApi(host=host, key=key)
    return client.upload_preview(collectionid, previewfile, previewmetadata)


class CollectionsApi(object):
    """
        API to manage the REST CRUD endpoints for collections
    """

    def __init__(self, client=None, host=None, key=None, username=None, password=None):

        """Set client if provided otherwise create new one"""
        if client:
            self.api_client = client
        else:
            self.client = ClowderClient(host=host, key=key, username=username, password=password)


    def add_preview(self, collection_id, preview_file, preview_metadata):
        """Upload a collection preview.

        Keyword arguments:
        collection_id -- the collection that is currently being processed
        preview_file -- the file containing the preview
        preview_metadata: any metadata to be associated with preview,
                        this can contain a section_id to indicate the
                        section this preview should be associated with.
        """

        # upload preview
        prev = self.client.post_file("previews", preview_file)

        # associate uploaded preview with original collection
        if collection_id and not (preview_metadata and preview_metadata['section_id']):
            self.client.post("collections/%s/previews/%s" % (collection_id, prev['id']))

        # associate metadata with preview
        if preview_metadata is not None:
            self.client.post("previews/%s/metadata" % prev['id'], preview_metadata)

        return prev['id']


    def create(self, name, description="", parent_id=None, space_id=None):
        """Create a new collection in Clowder.

        Keyword arguments:
        name -- name of new collection to create
        description -- description of new collection
        parent_id -- id of parent collection (or list of ids)
        space_id -- id of the space to add collection to
        """

        body = {
            "name": name,
            "description": description,
        }

        if parent_id:
            if isinstance(parent_id, list):
                body["parentId"] = parent_id
            else:
                body["parentId"] = [parent_id]
            if space_id:
                body["space"] = space_id
            result = self.client.post("collections/newCollectionWithParent", body)
        else:
            if space_id:
                body["space"] = space_id
            result = self.client.post("collections", body)

        return result['id']


    def delete(self, collection_id):
        """Delete a collection from Clowder.

        Keyword arguments:
        collection_id -- id of collection to delete
        """

        return self.client.delete("collections/%s" % collection_id)


    def delete_all_datasets(self, collection_id, recursive=True, delete_collections=False):
        """Delete all datasets from collection.

        Keyword arguments:
        collection_id -- the collection to walk
        recursive -- whether to also iterate across child collections
        delete_collections -- whether to also delete collections containing the datasets
        """

        dsapi = DatasetsApi(self.client)
        dslist = self.get_datasets(collection_id)
        for ds in dslist:
            dsapi.delete(ds['id'])

        if recursive:
            children = self.get_child_collections(collection_id)
            for child_coll in children:
                self.delete_all_datasets(child_coll['id'], recursive, delete_collections)

        if delete_collections:
            self.delete(collection_id)


    def get_all_collections(self):
        """Get all Collections in Clowder."""

        return self.client.get("/collections")


    def get_child_collections(self, collection_id):
        """List child collections of a collection.

        Keyword arguments:
        collection_id -- id of collection to get children of
        """

        return self.client.get("collections/%s/getChildCollections" % collection_id)


    def get_datasets(self, collection_id):
        """Get list of datasets in a collection.

        Keyword arguments:
        collection_id -- id of collection to get datasets of
        """

        return self.client.get("collections/%s/datasets" % collection_id)


    def submit_all_files_for_extraction(self, collection_id, extractor_name, extension=None, recursive=True):
        """Manually trigger an extraction on all files in a collection.

        This will iterate through all datasets in the given collection and submit them to
        the submit_extractions_by_dataset(). Does not operate recursively if there are nested collections.

        Keyword arguments:
        collection_id -- the collection UUID to submit
        extractor_name -- registered name of extractor to trigger
        extension -- extension to filter. e.g. 'tif' will only submit TIFF files for extraction
        recursive -- whether to also submit child collection files recursively (defaults to True)
        """

        dsapi = DatasetsApi(self.client)
        dslist = self.get_datasets(collection_id)
        for ds in dslist:
            dsapi.submit_all_files_for_extraction(ds['id'], extractor_name, extension)

        if recursive:
            children = self.get_child_collections(collection_id)
            for child_coll in children:
                self.submit_all_files_for_extraction(child_coll['id'], extractor_name, extension, recursive)


    def submit_all_datasets_for_extraction(self, collection_id, extractor_name, recursive=True):
        """Manually trigger an extraction on all datasets in a collection.

        This will iterate through all datasets in the given collection and submit them to
        the provided extractor.

        Keyword arguments:
        datasetid -- the dataset UUID to submit
        extractorname -- registered name of extractor to trigger
        recursive -- whether to also submit child collection datasets recursively (defaults to True)
        """

        dsapi = DatasetsApi(self.client)
        dslist = self.get_datasets(collection_id)
        for ds in dslist:
            dsapi.submit_extraction(ds['id'], extractor_name)

        if recursive:
            children = self.get_child_collections(collection_id)
            for child_coll in children:
                self.submit_all_datasets_for_extraction(child_coll['id'], extractor_name, recursive)
