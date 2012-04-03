import json

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado_pyvows import TornadoHTTPContext
from pyvows import Vows, expect

import trombi

COUCHDB_DEFAULT = 'http://localhost:5984'

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

def from_uri_context(address='localhost', db_name='foo', port=5984):
    class StaticCreation(TornadoHTTPContext):

        def setup(self):
            TornadoHTTPContext.setup(self)
            self.put('http://%s:%s/%s' % (address, port, db_name), body='')

        def teardown(self):
            self.delete('http://%s:%s/%s' % (address, port, db_name), body='')
            TornadoHTTPContext.teardown(self)

        def topic(self):
            if port:
                baseurl = 'http://%s:%s/%s' % (address, port, db_name)
            else:
                baseurl = 'http://%s/%s' % (address, db_name)
            db = trombi.from_uri(baseurl)
            return (baseurl, db_name, db)

        def should_have_correct_base_url(self, topic):
            baseurl, _, db = topic
            expect(db.baseurl).to_equal(baseurl)

        def should_have_correct_name(self, topic):
            _, name, db = topic
            expect(db.name).to_equal(name)

        def should_have_correct_server_type(self, topic):
            _, _, db = topic
            expect(db.server).to_be_instance_of(trombi.Server)
    return StaticCreation

def create_database(db_name='couchdb-database', teardown=True):

    class Context(TornadoHTTPContext):

        def topic(self):
            server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
            server.create(db_name, callback=self.stop)
            topic = self.wait()
            return topic

        def teardown(self):
            if teardown:
                self.delete('%s/%s/' % (COUCHDB_DEFAULT, db_name))

    return Context

def get_or_create_database(db_name='nonexistent', teardown=True):

    class Context(TornadoHTTPContext):

        def topic(self):
            server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
            server.get(db_name, create=True, callback=self.stop)
            return self.wait()

        def teardown(self):
            if teardown:
                self.delete('%s/%s/' % (COUCHDB_DEFAULT, db_name))

    return Context

def delete_database(db_name='delete'):

    class Context(TornadoHTTPContext):

        def topic(self):
            server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
            server.delete(db_name, callback=self.stop)
            return self.wait()

    return Context

@Vows.batch
class StaticCreationWithPort(from_uri_context()):
    pass

@Vows.batch
class StaticCreationWithoutPort(from_uri_context(port=None)):
    pass

database = 'couchdb-database'
@Vows.batch
class CannotConnect(TornadoHTTPContext):

    def topic(self):
        server = trombi.Server('http://localhost:39998', io_loop=self.io_loop)
        server.create(database, self.stop)
        return self.wait()

    def should_provide_an_error(self, topic):
        expect(topic.error).to_be_true()

    def should_have_error_code(self, topic):
        expect(topic.errno).to_equal(599)

    def should_have_error_message(self, topic):
        expect(topic.msg).to_equal('Unable to connect to CouchDB')

a_create_database = 'create'
@Vows.batch
class CreateDatabase(create_database(a_create_database)):

    def should_be_a_database(self, topic):
        expect(topic).to_be_instance_of(trombi.Database)

        class SuccessfullCreation(TornadoHTTPContext):

            def topic(self):
                response = self.get('%s/%s' % (COUCHDB_DEFAULT, '_all_dbs'))
                return json.loads(response.body)

            def should_contain_the_database(self, topic):
                expect(topic).to_include(a_create_database)


already_exists_database = 'another_db'
@Vows.batch
class DatabaseAlreadyExists(create_database(already_exists_database)):

    class CreateDatabaseAgain(create_database(already_exists_database)):
        
        def should_provide_an_error(self, topic):
            expect(topic.error).to_be_true()

        def should_have_error_code(self, topic):
            expect(topic.errno).to_equal(trombi.errors.PRECONDITION_FAILED)

        def should_have_error_message(self, topic):
            expect(topic.msg).to_equal(
                    "Database already exists: '%s'" % already_exists_database)

invalid_database_name = 'this name is invalid'
@Vows.batch
class InvalidDatabaseName(create_database(invalid_database_name)):
    
    def should_provide_an_error(self, topic):
        expect(topic.error).to_be_true()

    def should_have_error_code(self, topic):
        expect(topic.errno).to_equal(trombi.errors.INVALID_DATABASE_NAME)

    def should_have_error_message(self, topic):
        expect(topic.msg).to_equal("Invalid database name: '%s'" \
                % invalid_database_name)

nonexistent_database = 'nonexistent'
@Vows.batch
class GetOrCreateIfDatabaseNotExists(get_or_create_database(nonexistent_database)):
    
    def should_be_a_database(self, topic):
        expect(topic).to_be_instance_of(trombi.Database)

    def should_have_correct_name(self, topic):
        expect(topic.name).to_equal(nonexistent_database)
    
a_get_database = 'new'
@Vows.batch
class FirstCreateTheDatabase(create_database(a_get_database)):

    pass
    class ThenGetTheDatabase(get_or_create_database(a_get_database)):

        def should_be_a_database(self, topic):
            expect(topic).to_be_instance_of(trombi.Database)

        def should_have_correct_name(self, topic):
            expect(topic.name).to_equal(a_get_database)

a_delete_database = 'delete'
@Vows.batch
class FirstCreateDatabase(create_database(a_delete_database, teardown=False)):

    class ThenDeleteDatabase(delete_database(a_delete_database)):
        
        class CheckDeletionOfDatabase(TornadoHTTPContext):
            def topic(self):
                response = self.get('%s/_all_dbs' % COUCHDB_DEFAULT)
                all_dbs = json.loads(response.body)
                return all_dbs

            def should_not_contain_database(self, topic):
                expect(topic).not_to_include(a_delete_database)

@Vows.batch
class ListDatabases(TornadoHTTPContext):

    def topic(self):
        server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
        server.list(self.stop)
        response = self.wait()
        # response is a generator!
        return response

    def should_be_a_database(self, topic):
        expect(topic).to_be_instance_of(trombi.Database)

a_nonexistent_database = 'a_nonexistent_database'
@Vows.batch
class OpenNonexistingDatbase(TornadoHTTPContext):

    def topic(self):
        server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
        server.get(a_nonexistent_database, callback=self.stop)
        response = self.wait()
        return response

    def should_provide_an_error(self, topic):
        expect(topic.error).to_be_true()

    def should_have_error_code(self, topic):
        expect(topic.errno).to_equal(trombi.errors.NOT_FOUND)

    def should_have_error_message(self, topic):
        expect(topic.msg).to_equal(
                "Database not found: %s" % a_nonexistent_database)
