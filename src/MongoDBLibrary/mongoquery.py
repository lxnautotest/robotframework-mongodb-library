import ast
import json
import re
from bson.objectid import ObjectId
from pymongo import ReturnDocument
import logging

class MongoQuery(object):
    """
    Query handles all the querying done by the MongoDB Library. 
    """
    def pythonish_to_json_dict(self, text: str):
        """
        Parses a hybrid JSON/Python-style dict string into a valid Python dict.
        Supports:
        - Single-quoted keys and values
        - Python strings with apostrophes
        - JSON literals like false/null/true
        """

        # Normalize JSON literals to Python ones for ast.literal_eval
        fixed = text
        fixed = re.sub(r'\bfalse\b', 'False', fixed, flags=re.IGNORECASE)
        fixed = re.sub(r'\btrue\b', 'True', fixed, flags=re.IGNORECASE)
        fixed = re.sub(r'\bnull\b', 'None', fixed, flags=re.IGNORECASE)

        try:
            # Try parsing with Python's safe literal parser
            obj = ast.literal_eval(fixed)
            # Convert back to JSON-safe dict (ensures proper types)
            return json.loads(json.dumps(obj))
        except Exception as e:
            raise Exception(f"Error parsing pythonish to json dict: {e}")

    def get_mongodb_databases(self):
        """
        Returns a list of all of the databases currently on the MongoDB 
        server you are connected to.

        Usage is:
        | @{allDBs} | Get Mongodb Databases |
        | Log Many | @{allDBs} |
        | Should Contain | ${allDBs} | DBName |
        """
        allDBs = self._dbconnection.database_names()
        logging.debug("| @{allDBs} | Get Mongodb Databases |")
        return allDBs

    def get_mongodb_collections(self, dbName):
        """
        Returns a list of all of the collections for the database you
        passed in on the connected MongoDB server.

        Usage is:
        | @{allCollections} | Get MongoDB Collections | DBName |
        | Log Many | @{allCollections} |
        | Should Contain | ${allCollections} | CollName |
        """
        dbName = str(dbName)
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        allCollections = db.collection_names()
        logging.debug("| @{allCollections} | Get MongoDB Collections | %s |" % dbName)
        return allCollections

    def drop_mongodb_database(self, dbDelName):
        """
        Deletes the database passed in from the MongoDB server if it exists.
        If the database does not exist, no errors are thrown.

        Usage is:
        | Drop MongoDB Database | myDB |
        | @{allDBs} | Get MongoDB Collections | myDB |
        | Should Not Contain | ${allDBs} | myDB |
        """
        dbDelName = str(dbDelName)
        logging.debug("| Drop MongoDB Database | %s |" % dbDelName)
        try:
            self._dbconnection.drop_database('%s' % dbDelName)
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")

    def drop_mongodb_collection(self, dbName, dbCollName):
        """
        Deletes the named collection passed in from the database named.
        If the collection does not exist, no errors are thrown.

        Usage is:
        | Drop MongoDB Collection | myDB | CollectionName |
        | @{allCollections} | Get MongoDB Collections | myDB |
        | Should Not Contain | ${allCollections} | CollectionName |
        """
        dbName = str(dbName)
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        db.drop_collection('%s' % dbCollName)
        logging.debug("| Drop MongoDB Collection | %s | %s |" % (dbName, dbCollName))

    def validate_mongodb_collection(self, dbName, dbCollName):
        """
        Returns a string of validation info. Raises CollectionInvalid if 
        validation fails.

        Usage is:
        | ${allResults} | Validate MongoDB Collection | DBName | CollectionName |
        | Log | ${allResults} |
        """
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        allResults = db.validate_collection('%s' % dbCollName)
        logging.debug("| ${allResults} | Validate MongoDB Collection | %s | %s |" % (dbName, dbCollName))
        return allResults

    def get_mongodb_collection_count(self, dbName, dbCollName):
        """
        Returns the number records for the collection specified.

        Usage is:
        | ${allResults} | Get MongoDB Collection Count | DBName | CollectionName |
        | Log | ${allResults} |
        """
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        count = coll.count_documents({})
        logging.debug("| ${allResults} | Get MongoDB Collection Count | %s | %s |" % (dbName, dbCollName))
        return count

    def insert_mongodb_record(self, dbName, dbCollName, recordJSON):
        """ 
        The pymongo's insert_one() operation is performed. 

        | ${allResults} | Insert MongoDB Record | DBName | CollectionName | JSON |

        Enter a new record usage is:
        | ${inserted_id} | Insert MongoDB Record | foo | bar | {"timestamp":1, "msg":"Hello 1"} |
        | Log | ${inserted_id} |
        """
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        recordJSON = dict(json.loads(recordJSON))
        if '_id' in recordJSON:
            recordJSON['_id'] = ObjectId(recordJSON['_id'])
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        inserted = coll.insert_one(recordJSON)
        logging.debug("| ${inserted.inserted_id} | Insert MongoDB Records | %s | %s | %s |" % (dbName, dbCollName, recordJSON))
        return inserted.inserted_id

    def save_mongodb_records(self, dbName, dbCollName, recordJSON):
        """
        If to_save already has an "_id" then an update() (upsert) operation is 
        performed and any existing document with that "_id" is overwritten. 
        Otherwise an insert() operation is performed. In this case if manipulate 
        is True an "_id" will be added to to_save and this method returns the 
        "_id" of the saved document.

        | ${allResults} | Save MongoDB Records | DBName | CollectionName | JSON |

        Enter a new record usage is:
        | ${allResults} | Save MongoDB Records | foo | bar | {"timestamp":1, "msg":"Hello 1"} |
        | Log | ${allResults} |

        Update an existing record usage is:
        | ${allResults} | Save MongoDB Records | foo | bar | {"timestamp":1, "msg":"Hello 1"} |
        | Log | ${allResults} |
        """
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        recordJSON = dict(json.loads(recordJSON))
        if '_id' in recordJSON:
            recordJSON['_id'] = ObjectId(recordJSON['_id'])
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        allResults = coll.save(recordJSON)
        logging.debug("| ${allResults} | Save MongoDB Records | %s | %s | %s |" % (dbName, dbCollName, recordJSON))
        return allResults

    def update_many_mongodb_records(self, dbName, dbCollName, queryJSON, updateJSON, upsert=False):
        """
        Update many MongoDB records at ones based on the given query string and
        return number of modified documents.

        Usage is:
        | ${QueryJSON}  | Set Variable | {"type" : "basic_user" ,"in_use": false} |
        | ${UpdateJSON} | Set Variable | {"$set": {"in_use" : true}} |
        | &{allResults} | Update Many Mongodb Records | DBName | CollectionName | ${QueryJSON} | ${UpdateJSON} |
        | Log | ${allResults} |
        """
        db_name = str(dbName)
        collection_name = str(dbCollName)
        query_json = json.loads(queryJSON)
        update_json = json.loads(updateJSON)
        if '_id' in query_json:
            query_json['_id'] = ObjectId(queryJSON['_id'])
        try:
            db = self._dbconnection['%s' % (db_name,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % collection_name]
        allResults = coll.update_many(query_json, update_json, upsert=upsert)
        logging.debug("Matched: %i documents" % allResults.matched_count)
        logging.debug("| ${allResults} | Update Many MongoDB Records | %s | %s | %s | %s |" % (
            dbName, dbCollName, query_json, update_json))
        return allResults.modified_count

    def retrieve_all_mongodb_records(self, dbName, dbCollName, returnDocuments=False):
        """
        Retrieve ALL of the records in a give MongoDB database collection.
        Returned value must be single quoted for comparison, otherwise you will
        get a TypeError error.

        Usage is:
        | ${allResults} | Retrieve All MongoDB Records | DBName | CollectionName |
        | Log | ${allResults} |
        | Should Contain X Times | ${allResults} | '${recordNo1}' | 1 |
        """
        return self._retrieve_mongodb_records(dbName, dbCollName, '{}', returnDocuments=returnDocuments)

    def retrieve_some_mongodb_records(self, dbName, dbCollName, recordJSON, returnDocuments=False):
        """
        Retrieve some of the records from a given MongoDB database collection
        based on the JSON entered.
        Returned value must be single quoted for comparison, otherwise you will
        get a TypeError error.

        Usage is:
        | ${allResults} | Retrieve Some MongoDB Records | DBName | CollectionName | JSON |
        | Log | ${allResults} |
        | Should Contain X Times | ${allResults} | '${recordNo1}' | 1 |
        """
        logging.debug("| ${allResults} | Retrieve Some MongoDB Records | %s | %s | %s |" % (dbName, dbCollName, recordJSON))
        return self._retrieve_mongodb_records(dbName, dbCollName, recordJSON, returnDocuments=returnDocuments)

    def retrieve_and_update_one_mongodb_record(self, dbName, dbCollName, queryJSON, updateJSON,
                                               returnBeforeDocument=False):
        """
        Retrieve and update one record from a given MongoDB database collection
        based on the JSON query string. Return format is robot dictionary.
        ``returnBeforeDocument`` if return document should be before or after the update, default is ``False``.

        Usage is:
        | ${QueryJSON}  | Set Variable | {"type" : "basic_user" ,"in_use": false} |
        | ${UpdateJSON} | Set Variable | {"$set": {"in_use" : true}} |
        | &{allResults} | Retrieve and Update One Mongodb Record | DBName | CollectionName | ${QueryJSON} | ${UpdateJSON} |
        | Log | ${allResults} |
        """
        dbname = str(dbName)
        dbcollname = str(dbCollName)
        record_json = dict(json.loads(queryJSON))
        update_json = dict(json.loads(updateJSON))
        document_to_return = ReturnDocument.BEFORE if returnBeforeDocument is True else ReturnDocument.AFTER
        if '_id' in record_json:
            record_json['_id'] = ObjectId(record_json['_id'])
        try:
            db = self._dbconnection['%s' % (dbname,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbcollname]
        all_results = coll.find_one_and_update(record_json, update_json, return_document=document_to_return)
        logging.debug("| ${allResults} | Retrieve And Update One Mongodb Record | %s | %s | %s | %s | %s" % (
            dbname,
            dbcollname,
            queryJSON,
            updateJSON,
            returnBeforeDocument))
        return all_results

    def retrieve_mongodb_records_with_desired_fields(self, dbName, dbCollName, recordJSON, fields, return__id=True,
                                                     returnDocuments=False):
        """
        Retrieves from a document(s) the desired projection. In a sql terms: select a and b from table;
        For more details about querying records from Mongodb and comparison to sql see the
        [http://docs.mongodb.org/manual/reference/sql-comparison|Mongodb]
        documentation.

        In Mongodb terms would correspond: db.collection.find({ }, { fieldA: 1, fieldB: 1 })

        For usage of the dbName, dbCollName and recordJSON arguments, see the keyword
        ``Retrieve Some Mongodb Records`` documentation.

        fields argument control what field(s) are returned from the document(s),
        it is a comma separated string of fields. It is also possible to return fields
        inside of the array element, by separating field by dot notation. See the
        usage examples for more details how to use fields argument.

        return__id controls is the _id field also returned with the projections.
        Possible values are True and False

        The following usages assume a database name account, collection named users and
        that contain documents of the following prototype:
        {"firstName": "Clark", "lastName": "Kent", "address": {"streetAddress": "21 2nd Street", "city": "Metropolis"}}

        Usage is:
        | ${firstName} | Retrieve MongoDB Records With Desired Fields | account | users | {} | firstName | 0 |
        | ${address} | Retrieve MongoDB Records With Desired Fields | account | users | {} | address | ${false} | # Robot BuiltIn boolean value |
        | ${address_city} | Retrieve MongoDB Records With Desired Fields | account | users | {} | address.city | False |
        | ${address_city_and_streetAddress} | Retrieve MongoDB Records With Desired Fields | account | users | {} | address.city, address.streetAddress | False |
        | ${_id} | Retrieve MongoDB Records With Desired Fields | account | users | {} | firstName | True |
        =>
        | ${firstName} = [(u'firstName', u'Clark')] |
        | ${address} = [(u'address', {u'city': u'Metropolis', u'streetAddress': u'21 2nd Street'})] |
        | ${address_city} = [(u'address', {u'city': u'Metropolis'})] |
        | ${address_city_and_streetAddress} = [(u'address', {u'city': u'Metropolis', u'streetAddress': u'21 2nd Street'})] # Same as retrieving only address |
        | ${_id} = [(u'_id', ObjectId('...')), (u'firstName', u'Clark')] |

        """
        # Convert return__id to boolean value because Robot Framework returns False/True as Unicode
        try:
            if return__id.isdigit():
                pass
            else:
                return__id = return__id.lower()
                if return__id == 'false':
                    return__id = False
                else:
                    return__id = True
        except AttributeError:
            pass

        # Convert the fields string as a dictionary and handle _id field
        if fields:
            data = {}
            fields = fields.replace(' ', '')
            for item in fields.split(','):
                data[item] = True

            if return__id:
                data['_id'] = True
            elif not return__id:
                data['_id'] = False
            else:
                raise Exception('Not a boolean value for return__id: %s' % return__id)
        else:
            data = []

        logging.debug("| ${allResults} | retreive_mongodb_records_with_desired_fields | %s | %s | %s | %s | %s |" % (
            dbName, dbCollName, recordJSON, fields, return__id))
        return self._retrieve_mongodb_records(dbName, dbCollName, recordJSON, data, returnDocuments)

    def _retrieve_mongodb_records(self, dbName, dbCollName, recordJSON, fields=[], returnDocuments=False):
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        criteria = self.pythonish_to_json_dict(recordJSON)

        # handle _id column (ObjectId)
        if '_id' in criteria:
            criteria['_id'] = ObjectId(criteria['_id'])

        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        if fields:
            results = coll.find(criteria, fields)
        else:
            results = coll.find(criteria)
        if returnDocuments:
            return list(results)
        else:
            response = ''
            for d in results:
                response = '%s%s' % (response, d.items())
            return response

    def remove_mongodb_records(self, dbName, dbCollName, recordJSON):
        """
        Remove some of the records from a given MongoDB database collection
        based on the JSON entered.

        The JSON fed in must be double quoted but when doing a comparison, it
        has to be single quoted.  See Usage below

        Usage is:
        | ${allResults} | Remove MongoDB Records | ${MDBDB} | ${MDBColl} | {"_id": "4dacab2d52dfbd26f1000000"} |
        | Log | ${allResults} |
        | ${output} | Retrieve All MongoDB Records | ${MDBDB} | ${MDBColl} |
        | Should Not Contain | ${output} | '4dacab2d52dfbd26f1000000' |
        or
        | ${allResults} | Remove MongoDB Records | ${MDBDB} | ${MDBColl} | {"timestamp": {"$lt": 2}} |
        | Log | ${allResults} |
        | ${output} | Retrieve All MongoDB Records | ${MDBDB} | ${MDBColl} |
        | Should Not Contain | ${output} | 'timestamp', 1 |
        """
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        recordJSON = json.loads(recordJSON)
        if '_id' in recordJSON:
            recordJSON['_id'] = ObjectId(recordJSON['_id'])
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        allResults = coll.delete_many(recordJSON)
        logging.debug("| ${allResults} | Remove MongoDB Records | %s | %s | %s |" % (dbName, dbCollName, recordJSON))
        return allResults
    
    def aggregate_mongodb_records(self, dbName, dbCollName, aggregate_cond=None):
        """
        Returns the aggregated results based on the aggregate_cond.

        Usage is:
        | ${results} | Aggregate MongoDB Records | DBName | CollectionName | Aggregate_cond |
        """
        agg_cond = aggregate_cond or []
        agg_cond = json.loads(agg_cond)
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        logging.debug(f"Aggregate_cond: {agg_cond}")
        results = coll.aggregate(agg_cond)
        logging.debug("| ${results} | Aggregate MongoDB Records | %s | %s |" % (dbName, dbCollName))
        return list(results)

    def get_mongodb_collection_count_with_condition(self, dbName, dbCollName, conditionJSON = {}):
        """
        Returns the number records for the collection specified.

        Usage is:
        | ${allResults} | Get MongoDB Collection Count | DBName | CollectionName |
        | Log | ${allResults} |
        """
        dbName = str(dbName)
        dbCollName = str(dbCollName)
        criteria = dict(json.loads(conditionJSON))
        try:
            db = self._dbconnection['%s' % (dbName,)]
        except TypeError:
            self._builtin.fail("Connection failed, please make sure you have run 'Connect To Mongodb' first.")
        coll = db['%s' % dbCollName]
        count = coll.count_documents(criteria)
        logging.debug("| ${allResults} | Get MongoDB Collection Count | %s | %s |" % (dbName, dbCollName))
        return count
