import json

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado_pyvows import TornadoHTTPContext
from pyvows import Vows, expect

import trombi

COUCHDB_DEFAULT = 'http://localhost:5984'

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

document_database = 'document'
@Vows.batch
class CreateDocumentDatabase(TornadoHTTPContext):

    def topic(self):
        server = trombi.Server(COUCHDB_DEFAULT, io_loop=self.io_loop)
        server.get(document_database, create=True, callback=self.stop)
        return self.wait()

    def teardown(self):
        self.delete('%s/%s/' % (COUCHDB_DEFAULT, document_database))
        TornadoHTTPContext.teardown(self)

    class SaveAttachment(TornadoHTTPContext):
        
        def topic(self, database):
            database.set('custom', {'key': 'value'}, 
                    callback=self.stop)
            document = self.wait()
            document.attach('foobar', b'some textual data', callback=self.stop)
            self.wait()
            attachment_response = self.get('%s/%s/custom/foobar' % \
                    (COUCHDB_DEFAULT, document_database))
            return attachment_response

        def should_be_ok(self, topic):
            expect(topic.code).to_equal(200)

        def should_have_content(self, topic):
            expect(topic.body).to_equal(b'some textual data')

    class SaveAttachmentWithWrongRevision(TornadoHTTPContext):

        def topic(self, database):
            database.get('custom', callback=self.stop)
            document = self.wait()
            document.rev = '1-foobarbaz'
            document.attach('custom', b'some textual data', callback=self.stop)

            return self.wait()

        def should_provide_an_error(self, topic):
            expect(topic.error).to_be_true()

    class SaveLoadAttachment(TornadoHTTPContext):
        # NOTE: This is kinda hacky because the serial execution of nested vows
        # is done by sorting the class names! If the class gets renamed so that
        # its before (remove the Save) than this vow fails!
        def topic(self, database):
            database.get('custom', callback=self.stop)
            document = self.wait()
            document.load_attachment('foobar', callback=self.stop)
            attachment = self.wait()
            return attachment

        def should_have_content(self, topic):
            expect(topic).to_equal(b'some textual data')

    class LoadUnknownAttachment(TornadoHTTPContext):

        def topic(self, database):
            database.set('unknown', {'key': 'value'}, 
                    callback=self.stop)
            document = self.wait()
            document.attach('foobar', b'some textual data', callback=self.stop)
            self.wait()
            document.load_attachment('baz', callback=self.stop)
            attachment_response = self.wait()
            return attachment_response

        def should_provide_an_error(self, topic):
            expect(topic.error).to_be_true()

        def should_have_error_code(self, topic):
            expect(topic.errno).to_equal(trombi.errors.NOT_FOUND)

        def should_have_error_message(self, topic):
            expect(topic.msg).to_equal('Document is missing attachment')
    
    class LoadInlineAttachment(TornadoHTTPContext):
        # NOTE: if a document is created with an attachment inline e.g. while
        # inserting into the database we test here if an extra request is made
        # thus changing the internal _fetch method of the database.
        def topic(self, database):
            database.set('inline', {'key': 'value'}, 
                    attachments={'foobar': (None, b'some textual data')},
                    callback=self.stop)
            document = self.wait()
            original_fetch = document.db._fetch
            document.db._fetch = None
            document.load_attachment('foobar', callback=self.stop)
            attachment_response = self.wait()
            document.db._fetch = original_fetch
            return attachment_response

        def should_have_content(self, topic):
            expect(topic).to_equal(b'some textual data')
            
    class DeleteAttachment(TornadoHTTPContext):

        def topic(self, database):
            database.set('delete', {'key': 'value'}, callback=self.stop)
            document = self.wait()
            document.attach('foobar', b'some textual data', callback=self.stop)
            attachment_response = self.wait()
            document.delete_attachment('foobar', callback=self.stop)
            delete_response = self.wait()

            get_response = self.get('%s/%s/delete/foobar' % \
                    (COUCHDB_DEFAULT, database.name))
            return get_response

        def should_provide_an_error(self, topic):
            expect(topic.code).to_equal(404)

    class DeleteAttachmentWithWrongRevision(TornadoHTTPContext):

        def topic(self, database):
            database.set('wrong_rev', {'key': 'value'}, callback=self.stop)
            document = self.wait()
            document.attach('foobar', b'some textual data', callback=self.stop)
            attachment_response = self.wait()
            document.rev = '1-crazy'
            document.delete_attachment('foobar', callback=self.stop)
            delete_response = self.wait()

            return delete_response

        def should_provide_an_error(self, topic):
            expect(topic.error).to_be_true()
