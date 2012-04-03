import json

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado_pyvows import TornadoHTTPContext
from pyvows import Vows, expect

import trombi

COUCHDB_DEFAULT = 'http://localhost:5984'

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

def get_or_create_database(db_name='nonexistent', teardown=True):

    class Context(TornadoHTTPContext):

        def topic(self):
            server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
            server.get(db_name, create=True, callback=self.stop)
            return self.wait()

        def teardown(self):
            if teardown:
                self.delete('%s/%s/' % (COUCHDB_DEFAULT, db_name))
            TornadoHTTPContext.teardown(self)

    return Context

databas_database = 'database'
@Vows.batch
class CreateDatabaseDatabase(get_or_create_database(databas_database)):

    class DatabaseInfo(TornadoHTTPContext):

        def topic(self, database):
            database.info(self.stop)
            info_response = self.wait()
            return info_response

        def should_have_a_name(self, topic):
            expect(topic['db_name']).to_equal(databas_database)

        def should_have_no_documents(self, topic):
            expect(topic['doc_count']).to_equal(0)
        
        def should_have_update_sequence_info(self, topic):
            expect(topic).to_include('update_seq')

        def should_have_disk_size_info(self, topic):
            expect(topic).to_include('disk_size')

simple_document_database = 'simple_document_database'
@Vows.batch
class CreateSimpleDocumentDatabase(
        get_or_create_database(simple_document_database)):

    class SetDocument(TornadoHTTPContext):

        def topic(self, database):
            new_document = {'key': 'value'}
            database.set(new_document, self.stop)
            insert_response = self.wait()
            return ('_id', '_rev', insert_response)

        def should_be_a_document(self, topic):
            _, _, document = topic
            expect(document).to_be_instance_of(trombi.Document)

        def should_have_valid_id(self, topic):
            _, _, document = topic
            document = document.raw()
            expect(document).to_include('_id')
            expect(document['_id']).Not.to_be_empty()

        def should_have_valid_revision(self, topic):
            _, _, document = topic
            document = document.raw()
            expect(document).to_include('_rev')
            expect(document['_rev']).Not.to_be_empty()

        def should_contain_specified_value(self, topic):
            _, _, document = topic
            document = document.raw()
            expect(document['key']).to_equal('value')

    class SetDocumentWithSlash(SetDocument):

        def topic(self, database):
            database.set('something/with/slash', {'key': 'value'}, self.stop)
            insert_response = self.wait()
            return ('something/with/slash', '_rev', insert_response)

        class GetDocument(TornadoHTTPContext):

            def topic(self, doc_tuple, database):
                doc_id, _, document = doc_tuple
                database.get(doc_id, callback=self.stop)
                get_response = self.wait()
                return (document, get_response)

            def should_be_a_document(self, topic):
                _, actual_doc = topic
                expect(actual_doc).to_be_instance_of(trombi.Document)

            def should_be_correct(self, topic):
                expected_doc, actual_doc = topic
                expect(actual_doc.raw()).to_be_like(expected_doc.raw())

    class SetDocumentWithCustomId(SetDocumentWithSlash):

        def topic(self, database):
            database.set('custom_id', {'key': 'value'}, self.stop)
            insert_response = self.wait()
            return ('custom_id', '_rev', insert_response)
        
            class DeleteDocument(TornadoHTTPContext):

                def topic(self, doc_tuple, database):
                    _, _, document = doc_tuple
                    database.delete(document, callback=self.stop)
                    delete_repsonse = self.wait()
                    return delete_repsonse

                def should_not_provide_an_error(self, topic):
                    expect(topic.error).to_be_false()

                def should_be_a_database(self, topic):
                    expect(topic).to_be_instance_of(trombi.Database)


    class SetDocumentWithAttachment(SetDocument):

        def topic(self, database):
            database.set({'key': 'value'}, self.stop, 
                    attachments={'foo': (None, b'bar')})
            response = self.wait()
            return ('_id', '_rev', response)

        class GetDocumentWithAttachment(TornadoHTTPContext):

            def topic(self, doc_tuple, database):
                _, _, document = doc_tuple
                document = document.raw()
                database.get(document['_id'], callback=self.stop)
                get_response = self.wait()
                
                get_response.load_attachment('foo', self.stop)
                attachment = self.wait()
                return (document, get_response, attachment)

            def should_be_a_document(self, topic):
                _, actual_doc, _ = topic
                expect(actual_doc).to_be_instance_of(trombi.Document)

            def should_have_attachment(sefl, topic):
                _, _, attachment = topic
                expect(attachment).to_equal(b'bar')

        class GetAttachmentDirectlyFromDatabase(TornadoHTTPContext):

            def topic(self, doc_tuple, database):
                _, _, document = doc_tuple
                document = document.raw()
                database.get_attachment(document['_id'], 'foo', self.stop)
                attachment = self.wait()
                return attachment

            def should_be_the_attachment(self, topic):
                expect(topic).to_equal(b'bar')

        class GetNonExistentAttachment(TornadoHTTPContext):

            def topic(self, doc_tuple, database):
                _, _, document = doc_tuple
                document = document.raw()
                database.get_attachment(document['_id'], 'bar', self.stop)
                attachment = self.wait()
                return attachment

            def should_not_not_exist(self, topic):
                expect(topic).to_be_null()
        
    class AttachmentFromNonExistentDocument(TornadoHTTPContext):

        def topic(self, database):
            database.get_attachment('random_document', 'foo', self.stop)
            response = self.wait()
            return response

        def should_not_have_an_attachment(self, topic):
            expect(topic).to_be_null()


    class DeleteNonExistingDocument(TornadoHTTPContext):

        def topic(self, database):
            database.delete({'_id': 'does_not_exist', '_rev': '_foo'}, 
                    callback=self.stop)
            response = self.wait()
            return response

        def should_provide_an_erro(self, topic):
            expect(topic.error).to_be_true()

        def should_have_error_code(self, topic):
            expect(topic.errno).to_equal(trombi.errors.NOT_FOUND)

        def should_have_error_message(self, topic):
            expect(topic.msg).to_equal('missing')

    class DeleteDocumentWithWrongRevision(TornadoHTTPContext):

        def topic(self, database):
            document = {'key': 'value'}
            database.set(document, callback=self.stop)
            trombi_document = self.wait()
            trombi_document.rev = '1-foobar'
            database.delete(trombi_document, callback=self.stop)
            response = self.wait()
            return response

        def should_provide_an_erro(self, topic):
            expect(topic.error).to_be_true()

        def should_have_error_code(self, topic):
            expect(topic.errno).to_equal(trombi.errors.CONFLICT)

        def should_have_error_message(self, topic):
            expect(topic.msg).to_equal('Document update conflict.')

    class DeleteDocumentWithInvalidRevision(TornadoHTTPContext):

        def topic(self, database):
            document = {'key': 'value'}
            database.set(document, callback=self.stop)
            trombi_document = self.wait()
            trombi_document.rev = 'invalid'
            database.delete(trombi_document, callback=self.stop)
            response = self.wait()
            return response

        def should_provide_an_erro(self, topic):
            expect(topic.error).to_be_true()

        def should_have_error_code(self, topic):
            expect(topic.errno).to_equal(trombi.errors.BAD_REQUEST)

        def should_have_error_message(self, topic):
            expect(topic.msg).to_equal('Invalid rev format')

    class UpdateDocument(TornadoHTTPContext):

        def topic(self, database):
            document = {'key': 'value'}
            database.set(document, callback=self.stop)
            trombi_document = self.wait()
            trombi_document['new_key'] = 'new_value'
            database.set(trombi_document, callback=self.stop)
            new_trombi_document = self.wait()
            document.update({'new_key': 'new_value'})
            return (document, new_trombi_document)

        def should_contain_the_update(self, topic):
            expected_doc, actual_doc = topic
            expect(actual_doc).to_equal(expected_doc)

    class UpdateDocumentWithNewId(TornadoHTTPContext):

        def topic(self, database):
            document = {'key': 'value'}
            database.set('first', document, callback=self.stop)
            trombi_document = self.wait()
            trombi_document['new_key'] = 'new_value'
            # print trombi_document, trombi_document.raw()
            database.set('second', trombi_document, callback=self.stop)
            new_trombi_document = self.wait()
            # print new_trombi_document, new_trombi_document.raw()

            database.get('first', callback=self.stop)
            old_trombi_document = self.wait()
            # print old_trombi_document, old_trombi_document.raw()
            return (document, new_trombi_document, old_trombi_document)

        def should_be_different_documents(self, topic):
            _, new_trombi_document, old_trombi_document = topic
            expect(new_trombi_document).Not.to_equal(old_trombi_document)

        def initial_document_should_have_not_changed(self, topic):
            document, _, old_trombi_document = topic
            expect(old_trombi_document).to_equal(document)

    class SetInlineAttachmentWithCustomContentType(TornadoHTTPContext):

        def topic(self, database):
            attachments = {'foobar': 
                    ('application/x-custom', b'some textual data')}
            database.set('custom_content_type', {'key': 'value'}, 
                    callback=self.stop, attachments=attachments)
            document = self.wait()

            attachment_response = self.get('%s/%s/custom_content_type/foobar' \
                    % (COUCHDB_DEFAULT, database.name))
            return attachment_response

        def should_be_ok(self, topic):
            expect(topic.code).to_equal(200)

        def should_have_correct_content_type(self, topic):
            expect(topic.headers['Content-Type']).to_equal(
                    'application/x-custom')

        def should_have_correct_content(self, topic):
            expect(topic.body).to_equal(b'some textual data')

