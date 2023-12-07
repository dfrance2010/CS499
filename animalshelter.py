#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon 2023-9-18 20:54:13 
Last updated Sun 2023-12-03
version: 1.1
author: David France
email: david.france@snhu.edu
Purpose: Created to connect MongoDB database to Dash App dashboard,
         specifically the Austin Animal Shelter database.
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
from collections.abc import Mapping
import hashlib
from datetime import datetime

class AnimalShelter(object):
    """CRUD operations for MongoDB database """

    def __init__(self, database, collection):
        """Connect to specified database and collection"""
        
        DB = database
        COL = collection
        
        self.client = MongoClient()
        self.database = self.client['%s' % (DB)]
        self.collection = self.database['%s' % (COL)]

    
    def insert(self, data: dict) -> str:
        """Insert new document from dashboard fields"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")

        # Document is not yet complete, add calculated fields
        data = self.__add_fields(data)
        
        # Check if animal to insert is a rescue type
        if 'animal_type' in data and data['animal_type'] == 'Dog':
            data = self.__check_rescue_type(data)

        insert_result = self.collection.insert_one(data)  
        
        if insert_result.acknowledged:
            return f"New animal inserted with ID - {data['animal_id']}"

        return 'ERROR - animal not added'

    def insert_backup(self, data: dict) -> bool:
        """Insert complete document for backup purposes"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")

        insert_result = self.collection.insert_one(data)  

        return insert_result.acknowledged
        
    def find(self, data: dict) -> list:
        """"Find a document"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")

        # Not all fields need to be returned to dashboard
        cursor = self.collection.find(data, {'_id': 0, 'datetime': 0, 'monthyear': 0, 'rescue_type': 0})
          
        return self.__cursor_to_dict(cursor)
        
    def update(self, doc: dict, values: dict) -> int:
        """Update one or many documents"""
        
        # Check that data is in proper format
        if not isinstance(doc, Mapping) or not isinstance(values, Mapping): 
            raise Exception("Error - invalid data format")

        # If DOB is changed, ages need to be updated
        if 'date_of_birth' in values:
            values['age_upon_outcome'] = self.__age(values['date_of_birth'])
            values['age_upon_outcome_in_weeks'] = self.__age_in_weeks(values['date_of_birth'])
            
        # If individual animal is being updated, its id will be in one or both doc and values variables
        # If id is in values that means the id is being updated, so that is handled first
        if 'animal_id' in values:
            result = self.collection.update_one(doc, {'$set': values})  # Update animal
            animal = self.find({'animal_id': values['animal_id']})[0]   # Return updated animal 
            if animal['animal_type'] == 'Dog':                          # If animal is a dog, update rescue_type
                animal = self.__check_rescue_type(animal)                  
                self.collection.update_one({'animal_id': values['animal_id']}, {'$set': {'rescue_type': animal['rescue_type']}})
        elif 'animal_id' in doc:
            result = self.collection.update_one(doc, {'$set': values})  # Update animal
            animal = self.find({'animal_id': doc['animal_id']})[0]      # Return updated animal
            if animal['animal_type'] == 'Dog':                          # If animal is a dog, update rescue_type
                animal = self.__check_rescue_type(animal)
                self.collection.update_one({'animal_id': doc['animal_id']}, {'$set': {'rescue_type': animal['rescue_type']}})
        else:
            result = self.collection.update_many(doc, {'$set': values})
            # Return all animals that have been updated
            animals = self.find(values)  
            # For each updated animal, if it's a dog then update rescue_type
            for animal in animals:
                if animal['animal_type'] == 'Dog':                           
                    animal = self.__check_rescue_type(animal)                  
                    self.collection.update_one({'animal_id': animal['animal_id']}, {'$set': {'rescue_type': animal['rescue_type']}})
            
        return result.modified_count
    
    def delete(self, data: dict, many: bool = False) -> int:
        """Delete one or many documents"""
        
        # Check that data is in proper format
        if not isinstance(data, Mapping): 
            raise Exception("Error - invalid data format")
            
        if not many:
            result = self.collection.delete_one(data)
        else:
            result = self.collection.delete_many(data)
        
        return result.deleted_count

    def check_user(self, username: str, password: str) -> bool:
        """Determine if username/password pair is valid"""

        # Create hash functions for each variable
        user_hash = hashlib.sha256()
        pword_hash = hashlib.sha256()

        # Get salt value for username
        salt = self.__get_salt(username)

        username += salt
        password += salt
        
        # Hash the input username/password pair
        user_hash.update(username.encode('utf8'))
        pword_hash.update(password.encode('utf8'))

        # If username/password pair exists, it will return a cursor
        result = self.collection.find({user_hash.hexdigest(): pword_hash.hexdigest()})
        
        return len(self.__cursor_to_dict(result)) > 0

    def check_permission(self, username: str, password: str) -> bool:
        """Check if user has read/write or read-only permission"""

        # Get salt value for username
        salt = self.__get_salt(username)
        
        read_write = 'read/write' + salt
        tf = 'True' + salt

        # Create hash functions for each variable
        user_hash = hashlib.sha256()
        pword_hash = hashlib.sha256()
        rw_hash = hashlib.sha256()
        tf_hash = hashlib.sha256()

        # Encode each variable using the hash function
        user_hash.update((username+salt).encode('utf8'))
        pword_hash.update((password+salt).encode('utf8'))
        rw_hash.update(read_write.encode('utf8'))
        tf_hash.update(tf.encode('utf8'))

        # Get document for username/password pair
        result = self.collection.find({user_hash.hexdigest(): pword_hash.hexdigest()})

        # Insert key/value pairs from result to compare read/write permission
        document = {}
        for doc in result:
            for key, value in doc.items():
                document[str(key)] = str(value)

        # Return if value for key 'read/write' is 'True'
        return document[rw_hash.hexdigest()] == tf_hash.hexdigest()

    # Return the salt value for a given user
    def __get_salt(self, user):
        username = hashlib.sha256()
        username.update(user.encode('utf8'))

        # Connect to salt database
        salt_client = MongoClient()
        salt_db = self.client['%s' % ('Other')]
        
        result = self.__cursor_to_dict(salt_db.misc.find({'user': username.hexdigest()}))
        # If user doesn't exist, return 
        if len(result) < 1:
            return 'none'

        return result[0]['salt']
    
    def name_validation(self, name: str) -> bool:
        """Validate name for data input"""

        if len(name) > 15:
            return False

        characters = ['*', '-', '.', ' ']
        for char in name:
            if not char.isalpha() and char not in characters:
                return False

        return True

    def check_id(self, id: str) -> bool:
        """Validate ID for data update"""

        try:
            animal = self.find({'animal_id': id})[0]
            return True
        except:
            return False
            
        
    # Check if animal fits into a rescue_type, return updated dictionary ready to insert
    def __check_rescue_type(self, dict):
        # Animal can fit more than one rescue type, or be updated to fit none, each type gets inserted into array
        rescue_types = []

        water_breeds = ['Chesa Bay Retr Mix',
                        'Labrador Retriever Mix',
                        'Newfoundland']
        mountain_breeds = ['German Shepherd', 
                          'Alaskan Malamute', 
                          'Old English Sheepdog',
                          'Siberian Husky',
                          'Rottweiler']
        disaster_breeds = ['Doberman Pinsch', 
                          'German Shepherd', 
                          'Golden Retriever',
                          'Bloodhound',
                          'Rottweiler']
        
        # Append array if animal fits water type
        if dict['breed'] in water_breeds and dict['sex_upon_outcome'] == 'Intact Female' and dict['age_upon_outcome_in_weeks'] <= 156:
            rescue_types.append('water')
            
        # Append array if animal fits mountain/wilderness type
        if dict['breed'] in mountain_breeds and dict['sex_upon_outcome'] == 'Intact Male' and dict['age_upon_outcome_in_weeks'] <= 156:
            rescue_types.append('mountain_wilderness')
            
        # Append array if animal fits disaster/tracking type
        if dict['breed'] in disaster_breeds and dict['sex_upon_outcome'] == 'Intact Male' and dict['age_upon_outcome_in_weeks'] <= 300:
            rescue_types.append('disaster_tracking')
            
        # Append dictionary to insert into database. Empty dictionaries are still inserted,
        # which will take away categories from animals that have been updated to no 
        # longer fit into a rescue category
        dict['rescue_type'] = rescue_types

        return dict

    # Calculate and add fields to animal being inserted
    # Order matters to keep the data structure in line with dashboard data table
    def __add_fields(self, data):
        new_data = {}
        new_data['row'] = self.__next_row()
        new_data['age_upon_outcome'] = self.__age(data['date_of_birth'])
        new_data['animal_id'] = self.__next_id()
        
        if 'animal_type' in data:
            new_data['animal_type'] = data['animal_type']
        else:
            new_data['animal_type'] = ''
            
        if 'breed' in data:
            new_data['breed'] = data['breed']
        else:
            new_data['breed'] = ''
            
        if 'color' in data:
            new_data['color'] = data['color']
        else:
            new_data['color'] = ''
        
        if 'date_of_birth' in data:
            new_data['date_of_birth'] = data['date_of_birth']
            new_data['datetime'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_data['monthyear'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        else:
            new_data['date_of_birth'] = ''
            new_data['datetime'] = ''
            new_data['monthyear'] = ''
            
        if 'name' in data:
            new_data['name'] = data['name']
        else:
            new_data['name'] = ''
            
        if 'outcome_subtype' in data:
            new_data['outcome_subtype'] = data['outcome_subtype']
        else:
            new_data['outcome_subtype'] = ''
            
        if 'outcome_type' in data:
            new_data['outcome_type'] = data['outcome_type']
        else:
            new_data['outcome_type'] = ''
            
        if 'sex_upon_outcome' in data:
            new_data['sex_upon_outcome'] = data['sex_upon_outcome']
        else:
            new_data['sex_upon_outcome'] = ''
            
        if 'location_lat' in data:
            new_data['location_lat'] = data['location_lat']
            new_data['location_long'] = data['location_long']
        else:
            new_data['location_lat'] = 0.0
            new_data['location_long'] = 0.0
            
        if 'date_of_birth' in data:    
            new_data['age_upon_outcome_in_weeks'] = self.__age_in_weeks(data['date_of_birth'])
        else:
            new_data['age_upon_outcome_in_weeks'] = 0.0
            
        return new_data
        
    # Return next animal_id. Used when creating new animals.
    def __next_id(self):
        last_id = self.collection.find_one(sort=[('animal_id', -1)], projection=['animal_id'])
        id = int(last_id['animal_id'][1:])
        id += 1
        return f"A{id}"

    # Return next 'row' number. Used when creating new animals.
    def __next_row(self):
        last_row = self.collection.find_one(sort=[('row', -1)], projection=['row'])
        next_row = last_row['row'] + 1
        return next_row

    # Return age string from birthdate
    def __age(self, date) -> str:
        dob = datetime.strptime(date, "%Y-%m-%d")
        days = (datetime.now() - dob).days
        s = ''
        if days < 7:
            if days > 1:
                s = 's'
            return f'{days} day{s}'
        elif days < 30:
            weeks = days // 7
            if weeks > 1:
                s = 's'
            return f'{weeks} week{s}'
        elif days < 365:
            months = days // 30
            if months > 1:
                s = 's'
            return f'{months} month{s}'
        else:
            years = days // 365
            if years > 1:
                s = 's'

        return f'{years} year{s}'
    
    # Return age in weeks from birthdate
    def __age_in_weeks(self, date) -> float:
        dob = datetime.strptime(date, "%Y-%m-%d")
        days = (datetime.now() - dob).days
        return days / 7
            
    # Private function to convert cursor to list of dictionaries
    # Source: https://stacktuts.com/how-to-convert-a-pymongo-cursor-cursor-into-a-dict-in-python
    def __cursor_to_dict(self, cursor):
        result = []
        for doc in cursor:
            dictionary = dict(doc)
            result.append(dictionary)
            
        return result
    
    
    


