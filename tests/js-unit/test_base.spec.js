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
    jQuery.ajax.and.returnValue(JSON.stringify({'name': 'somerepo'}));
  });

  it('test-save-without-id', async function(){
    let model = new BaseModel();
    spyOn(model, '_get_save_data');
    await model.save();
    expect(jQuery.ajax.calls.allArgs()[0][0]['type']).toEqual('post');
    expect(model.name).toEqual('somerepo');
  });

  it('test-save-with-id', async function(){
    let model = new BaseModel();
    model.id = 'someid';
    spyOn(model, '_get_save_data');
    await model.save();
    expect(jQuery.ajax.calls.allArgs()[0][0]['type']).toEqual('put');
    expect(model.name).toEqual('somerepo');
  });

  it('test-get', async function(){
    let model = await BaseModel.get(BaseModel, {'name': 'somename'});
    expect(model.name).toEqual('somerepo');
  });

  it('test-list', async function(){
    jQuery.ajax.and.returnValue(JSON.stringify(
      {'items': [{'name': 'somerepo'}, {'name': 'otherrepo'}]}));
    let models = await BaseModel.list(BaseModel, {'someattr': 'value'});
    expect(models[1].name).toEqual('otherrepo');
  });

  it('test-delete-without-id', async function(){
    let model = new BaseModel();
    var threw = false;
    try{
      await model.delete();
    }catch(e){
      threw = true;
    };
    expect(threw).toBe(true);
  });

  it('test-delete', async function(){
    let model = new BaseModel();
    model.id = 'some-id';
    await model.delete();
    expect(jQuery.ajax).toHaveBeenCalled();
  });

  it('test-get-save-data', function(){
    let model = new BaseModel();
    model.name = 'some-name';
    let data = model._get_save_data();
    let expected = {'name': 'some-name'};
    expect(data).toEqual(expected);
  });

  it('test-format-query', function(){
    let kw = {'a': 'b'};
    let expected = '?a=b&';
    let returned = BaseModel._format_query(kw);
    expect(returned).toEqual(expected);
  });

  it('test-update-object', function(){
    let model = new BaseModel();
    let obj = {'some': 'thing'};
    BaseModel._update_object(model, obj);
    expect(model.some).toEqual('thing');
  });

});
