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
    this.model = new BaseModel({'id': 'some-id'});
  });

  it('test-get-url-delete', function(){
    let method = 'delete';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);
  });

  it('test-get-url-update', function(){
    let method = 'update';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);

  });

  it('test-get-url-read-with-id', function(){
    let method = 'read';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model);
    let expected = 'http://bla.com/api/?id=some-id';
    expect(url).toEqual(expected);
  });

  it('test-get-url-create', function(){
    let method = 'create';
    this.model._api_url = 'http://bla.com/api/';
    let url = _get_url(method, this.model, false);
    let expected = 'http://bla.com/api/';
    expect(url).toEqual(expected);
  });

  it('test-sync', async function(){
    let method = 'create';
    this.model._api_url = 'http://bla.com/api/';
    let options = {};
    await this.model.sync(method, this.model, options);
    let expected = 'http://bla.com/api/';
    expect(options.url).toEqual(expected);
  });

  it('test-parse-items', function(){
    let data = {'items': [{'bla': true}]};
    let parsed = this.model.parse(data);
    expect(parsed['bla']).toBe(true);
  });

  it('test-parse-obj', function(){
    let data = {'bla': true};
    let parsed = this.model.parse(data);
    expect(parsed['bla']).toBe(true);
  });

  it('test-fetch', function(){
    this.model.fetch({'bla': 'ble'});
    expect(this.model._has_used_query).toBe(true);
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
