// Copyright 2018 Juca Crispim <juca@poraodojuca.net>

// This file is part of toxicbuild.

// toxicbuild is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// toxicbuild is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

describe("BaseModelTest", function(){

  beforeEach(function(){
    spyOn(jQuery, 'ajax');
  });

  it('test-get-url-delete', function(){
    let method = 'delete';
    let obj = new BaseModel({'id': 'some-id'});
    obj._api_url = 'http://bla.com/api/';
    let url = _get_url(method, obj);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);
  });

  it('test-get-url-update', function(){
    let method = 'update';
    let obj = new BaseModel({'id': 'some-id'});
    obj._api_url = 'http://bla.com/api/';
    let url = _get_url(method, obj);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);

  });

  it('test-get-url-read-with-id', function(){
    let method = 'read';
    let obj = new BaseModel({'id': 'some-id'});
    obj._api_url = 'http://bla.com/api/';
    let url = _get_url(method, obj);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);
  });

  it('test-get-url-read-without-id', function(){
    let method = 'read';
    let obj = new BaseModel({'id': 'some-id'});
    obj._api_url = 'http://bla.com/api/';
    let url = _get_url(method, obj, false);
    let expected = 'http://bla.com/api/';
    expect(url).toEqual(expected);
  });

  it('test-get-url-create', function(){
    let method = 'create';
    let obj = new BaseModel({'id': 'some-id'});
    obj._api_url = 'http://bla.com/api/';
    let url = _get_url(method, obj, false);
    let expected = 'http://bla.com/api/';
    expect(url).toEqual(expected);
  });

  it('test-sync', async function(){
    let method = 'create';
    let obj = new BaseModel({'id': 'some-id'});
    obj._api_url = 'http://bla.com/api/';
    let options = {};
    await obj.sync(method, obj, options);
    let expected = 'http://bla.com/api/';
    expect(options.url).toEqual(expected);
  });

});

describe('BaseCollectionTest', function(){

  it('test-parse', function(){
    let data = {'items': [{'some': 'thing'}]};
    let collection = new BaseCollection();
    let expected = [{'some': 'thing'}];
    let returned = collection.parse(data);
    expect(returned).toEqual(expected);
  });
});
