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

describe('SlaveTest', function(){

  beforeEach(function(){
    spyOn(jQuery, 'ajax');
    let window_spy = jasmine.createSpy();
    window_spy.TOXIC_API_URL = 'http://localhost:1234/';
    window = window_spy;
  });

  it('test-get', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify({'name': 'someslave'}));
    let slave = await Slave.get({'id': 'someid'});
    expect(slave.name).toEqual('someslave');
  });

  it('test-list', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify(
      {'items': [{'name': 'someslave'}, {'name': 'otherslave'}]}));
    let slaves = await Slave.list();
    expect(slaves.length).toEqual(2);
  });

});
