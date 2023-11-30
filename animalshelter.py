#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 20:54:13 2023

@author: davidfrance_snhu
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
from collections.abc import Mapping

class AnimalShelter(object):
    """CRUD operations for 'AAC' database, 'animals' collection in MongoDB """

    def __init__(self):
        #self, user: str, password: str
        # Initializing the MongoClient. Variables make this class
        # function only for AAC database, animals collection, on the 
        # given Apporto environment.
        #
        # USER = user
        # PASS = password
        HOST = 'nv-desktop-services.apporto.com'
        PORT = 27017
        DB = 'AAC'
        COL = 'animals'
        #
        # Initialize Connection
        #
        # self.client = MongoClient('mongodb://%s:%s@%s:%d' % (USER,PASS,HOST,PORT))
        self.client = MongoClient()
        self.database = self.client['%s' % (DB)]
        self.collection = self.database['%s' % (COL)]

    
    def insert(self, data: dict) -> bool:
        """Insert new document"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")
            
        insert_result = self.database.animals.insert_one(data)  
        
        return insert_result.acknowledged

    
    def find(self, data: dict) -> list:
        """"Find a document"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")
        
        cursor = self.collection.find(data)
         
        return self.__cursor_to_dict(cursor)
        
    def update(self, doc: dict, values: dict, many: bool = True) -> int:
        """Update one or many documents"""
        
        # Check that data is in proper format
        if not isinstance(doc, Mapping) or not isinstance(values, Mapping): 
            raise Exception("Error - invalid data format")
            
        if many: 
            result = self.collection.update_many(doc, {'$set': values})
        else: 
            result = self.collection.update_one(doc, {'$set': values})
        
        return result.modified_count
    
    def delete(self, data: dict, many: bool = False) -> int:
        """Delete one or many documents"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")
            
        if many:
            result = self.collection.delete_many(data)
        else:
            result = self.collection.delete_many(data)
        
        return result.deleted_count
            
    # Private function to convert cursor to list of dictionaries
    # Source: https://stacktuts.com/how-to-convert-a-pymongo-cursor-cursor-into-a-dict-in-python
    def __cursor_to_dict(self, cursor):
        result = []
        for doc in cursor:
            dictionary = dict(doc)
            result.append(dictionary)
            
        return result
    
    
    


