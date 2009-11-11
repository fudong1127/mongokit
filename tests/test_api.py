#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009, Nicolas Clairon
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University of California, Berkeley nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from mongokit import *
from pymongo.objectid import ObjectId

CONNECTION = Connection()

class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.collection = CONNECTION['test']['mongokit']
        
    def tearDown(self):
        CONNECTION['test'].drop_collection('mongokit')
        CONNECTION['test'].drop_collection('version')
        CONNECTION['test'].drop_collection('other_version')
        CONNECTION['test'].drop_collection('versionned_mongokit')

    def test_save(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bla":{
                    "foo":unicode,
                    "bar":int,
                },
                "spam":[],
            }
        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 42
        id = mydoc.save()
        assert isinstance(id['_id'], unicode)
        assert id['_id'].startswith("MyDoc"), id

        saved_doc = self.collection.find_one({"bla.bar":42})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

        mydoc = MyDoc()
        mydoc["bla"]["foo"] = u"bar"
        mydoc["bla"]["bar"] = 43
        id = mydoc.save(uuid=False)
        assert isinstance(id['_id'], ObjectId)

        saved_doc = self.collection.find_one({"bla.bar":43})
        for key, value in mydoc.iteritems():
            assert saved_doc[key] == value

    def test_save_without_collection(self):
        class MyDoc(MongoDocument):
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["foo"] = 1
        self.assertRaises(ConnectionError, mydoc.save)

    def test_delete(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc['_id'] = 'foo'
        mydoc["foo"] = 1
        mydoc.save()
        assert MyDoc.all().count() == 1
        mydoc = MyDoc.get_from_id('foo')
        assert mydoc['foo'] == 1
        mydoc.delete()
        assert MyDoc.all().count() == 0
        
    def test_generate_skeleton(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":int},
                "bar":unicode
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":None}, "bar":None}, a

    def test_generate_skeleton2(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":[int]},
                "bar":{unicode:{"egg":int}}
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[]}, "bar":{}}, a

    def test_generate_skeleton3(self):
        class A(SchemaDocument):
            structure = {
                "a":{"foo":[int], "spam":{"bla":unicode}},
                "bar":{unicode:{"egg":int}}
            }
        a = A(gen_skel=False)
        assert a == {}
        a.generate_skeleton()
        assert a == {"a":{"foo":[], "spam":{"bla":None}}, "bar":{}}, a

    def test_get_from_id(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int,
            }
        mydoc = MyDoc()
        mydoc["_id"] = "bar"
        mydoc["foo"] = 3
        mydoc.save()
        fetched_doc = MyDoc.get_from_id("bar")
        assert mydoc == fetched_doc
        assert isinstance(fetched_doc, MyDoc)

    def test_all(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int,
                "bar":{"bla":int},
            }
        for i in range(10):
            mydoc = MyDoc()
            mydoc["foo"] = i
            mydoc["bar"]['bla'] = i
            mydoc.save()
        for i in MyDoc.all({"foo":{"$gt":4}}):
            assert isinstance(i, MyDoc)
        docs_list = [i["foo"] for i in MyDoc.all({"foo":{"$gt":4}})]
        assert docs_list == [5,6,7,8,9]
        # using limit/count
        assert MyDoc.all().count() == 10, MyDoc.all().count()
        assert MyDoc.all().limit(1).count() == 10, MyDoc.all().limit(1).count()
        assert MyDoc.all().where('this.foo').count() == 9 #{'foo':0} is not taken
        assert MyDoc.all().where('this.bar.bla').count() == 9 #{'foo':0} is not taken
        assert MyDoc.all().hint([('foo', 1)])
        assert [i['foo'] for i in MyDoc.all().sort('foo', -1)] == [9,8,7,6,5,4,3,2,1,0]
        allPlans = MyDoc.all().explain()['allPlans']
        assert allPlans == [{u'cursor': u'BasicCursor', u'startKey': {}, u'endKey': {}}]
        next_doc =  MyDoc.all().sort('foo',1).next()
        assert isinstance(next_doc, MyDoc)
        assert next_doc['foo'] == 0
        assert len(list(MyDoc.all().skip(3))) == 7, len(list(MyDoc.all().skip(3)))
        assert isinstance(MyDoc.all().skip(3), MongoDocumentCursor)

    def test_one(self):
        class MyDoc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "foo":int
            }
        mydoc = MyDoc()
        mydoc['foo'] = 0
        mydoc.save()
        mydoc = MyDoc.one()
        assert mydoc["foo"] == 0
        assert isinstance(mydoc, MyDoc)
        for i in range(10):
            mydoc = MyDoc()
            mydoc["foo"] = i
            mydoc.save()
        self.assertRaises(MultipleResultsFound, MyDoc.one)

    def test_fetch(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc_b":{"bar":int},
            }
        # creating DocA
        for i in range(10):
            mydoc = DocA()
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = DocB()
            mydoc['doc_b']["bar"] = i
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert DocA.all().count() == 15

        # fetch get only the corresponding documents:
        assert DocA.fetch().count() == 10, DocA.fetch().count()
        assert DocB.fetch().count() == 5
        index = 0
        for doc in DocA.fetch():
            assert doc == {'_id':doc['_id'], 'doc_a':{'foo':index}}, doc
            index += 1

        #assert DocA.fetch().limit(12).count() == 10, DocA.fetch().limit(1).count() # ???
        assert DocA.fetch().where('this.doc_a.foo > 3').count() == 6

    def test_fetch_with_query(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bar":unicode,
                "doc_a":{'foo':int},
            }
        class DocB(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "bar":unicode,
                "doc_b":{"bar":int},
            }

        # creating DocA
        for i in range(10):
            mydoc = DocA()
            if i % 2 == 0:
                mydoc['bar'] = u"spam"
            else:
                mydoc['bar'] = u"egg"
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = DocB()
            if i % 2 == 0:
                mydoc['bar'] = u"spam"
            else:
                mydoc['bar'] = u"egg"
            mydoc['doc_b']["bar"] = i
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert DocA.all().count() == 15
        assert DocA.fetch().count() == 10, DocA.fetch().count()
        assert DocB.fetch().count() == 5

        assert DocA.fetch({'bar':'spam'}).count() == 5
        assert DocB.fetch({'bar':'spam'}).count() == 3

    def test_fetch_inheritance(self):
        class Doc(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc":{'bla':int},
            }
        class DocA(Doc):
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(DocA):
            structure = {
                "doc_b":{"bar":int},
            }
        # creating DocA
        for i in range(10):
            mydoc = DocA()
            mydoc['doc']["bla"] = i+1
            mydoc['doc_a']["foo"] = i
            mydoc.save()
        # creating DocB
        for i in range(5):
            mydoc = DocB()
            mydoc['doc']["bla"] = i+1
            mydoc['doc_a']["foo"] = i
            mydoc['doc_b']["bar"] = i+2
            mydoc.save()

        # all get all documents present in the collection (ie: 15 here)
        assert DocA.all().count() == 15

        # fetch get only the corresponding documents:
        # DocB is a subclass of DocA and have all fields of DocA so
        # we get all doc here
        assert DocA.fetch().count() == 15, DocA.fetch().count()
        # but only the DocB as DocA does not have a 'doc_a' field
        assert DocB.fetch().count() == 5
        index = 0
        for doc in DocB.fetch():
            assert doc == {'_id':doc['_id'], 'doc_a':{'foo':index}, 'doc':{'bla':index+1}, "doc_b":{'bar':index+2}}, (doc, index)
            index += 1

        #assert DocA.fetch().limit(12).count() == 10, DocA.fetch().limit(1).count() # ???
        assert DocA.fetch().where('this.doc_a.foo > 3').count() == 7

    def test_fetch_one(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc_a":{'foo':int},
            }
        class DocB(DocA):
            structure = {
                "doc_b":{"bar":int},
            }

        # creating DocA
        mydoc = DocA()
        mydoc['doc_a']["foo"] = 1
        mydoc.save()
        # creating DocB
        mydoc = DocB()
        mydoc['doc_b']["bar"] = 2
        mydoc.save()

        assert DocB.fetch_one()
        self.assertRaises(MultipleResultsFound, DocA.fetch_one)


    def test_skip_validation(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc_a":{'foo':int},
            }

        # creating DocA
        mydoc = DocA()
        mydoc['doc_a']["foo"] = u'bar' 
        self.assertRaises(SchemaTypeError, mydoc.save)
        mydoc.save(validate=False)

        DocA.skip_validation = True

        # creating DocA
        mydoc = DocA()
        mydoc['doc_a']["foo"] = u'foo' 
        self.assertRaises(SchemaTypeError, mydoc.save, validate=True)
        mydoc.save()


    def test_connection(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc_a":{'foo':int},
            }
        assert DocA.connection == Connection("localhost", 27017)
        assert DocA.collection == Connection("localhost", 27017)['test']['mongokit']

 
        class DocB(DocA):pass
        assert DocB.connection == Connection("localhost", 27017)
        assert DocB.collection == Connection("localhost", 27017)['test']['mongokit']

        class DocC(DocB):
            db_host = "127.0.0.2"
        assert DocC.connection == Connection("127.0.0.2", 27017)
        assert DocC.collection == Connection("127.0.0.2", 27017)['test']['mongokit']

        class DocD(DocC):
            db_name = "foo"
        assert DocD.connection == Connection("127.0.0.2", 27017), DocD.connection
        assert DocD.collection == Connection("127.0.0.2", 27017)['foo']['mongokit'], DocD.collection

        class BadDoc(MongoDocument):
            structure = {}

        assert not hasattr(BadDoc, 'connection')

        class ShareConnection(MongoDocument):
            connection = Connection()
            structure = {}

        class ShareDocA(ShareConnection):pass
        class ShareDocB(ShareConnection):pass
        assert ShareDocA.connection == ShareDocB.connection
        assert id(ShareDocA.connection) == id(ShareDocB.connection)

    def test_get_collection(self):
        class DocA(MongoDocument):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "doc_a":{'foo':int},
            }
        assert DocA.collection == Connection("localhost", 27017)['test']['mongokit']
        assert DocA.get_collection(db_name="foo", collection_name="bar") == Connection('localhost', 27017)['foo']['bar']
        assert DocA.get_collection(collection_name="bar") == Connection('localhost', 27017)['test']['bar']
        assert DocA.get_collection(db_host="127.0.0.2", collection_name="bar") == Connection('127.0.0.2', 27017)['test']['bar']


    def test_all_with_dynamic_collection(self):
        class Section(MongoDocument):
            db_name = 'test'
            structure = {"section":int}

        s = Section(collection_name='section')
        s['section'] = 1
        s.save()

        s = Section(collection_name='section')
        s['section'] = 2
        s.save()

        s = Section(collection_name='other_section')
        s['section'] = 1
        s.save()

        s = Section(collection_name='other_section')
        s['section'] = 2
        s.save()


        sect_col = Section.get_collection(collection_name='section')
        sects = [s.collection.name() == 'section' and s.db.name() == 'test' for s in Section.all({}, collection=sect_col)] 
        print  [s for s in Section.all(collection=sect_col)] 
        assert len(sects) == 2, len(sects)
        assert any(sects)
        sects = [s.collection.name() == 'section' and s.db.name() == 'test' for s in Section.fetch( collection=sect_col)]
        assert len(sects) == 2
        assert any(sects)

        sect_col = Section.get_collection(collection_name='other_section')
        sects = [s.collection.name() == 'other_section' and s.db.name() == 'test' for s in Section.all({}, collection=sect_col)] 
        assert len(sects) == 2
        assert any(sects)
        sects = [s.collection.name() == 'other_section' and s.db.name() == 'test' for s in Section.fetch( collection=sect_col)]
        assert len(sects) == 2
        assert any(sects)


