// Copyright 2018 Juca Crispim <juca@poraodojuca.net>

// This file is part of toxicbuild.

// toxicbuild is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// toxicbuild is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

describe('NotificationTest', function(){

  beforeEach(function(){
    this.model = new Notification();
    this.model.set('name', 'notif');
  });

  it('test-enable', async function(){
    spyOn(Notification.prototype,'_request2api');
    await this.model.enable('some-repo-id', {field: 'val'});
    let url = this.model._request2api.calls.allArgs()[0][1];
    let method = this.model._request2api.calls.allArgs()[0][0];
    let expected_url = this.model._api_url + 'notif/some-repo-id';
    expect(url).toEqual(expected_url);
    expect(method).toEqual('post');
  });

  it('test-disable', async function(){
    spyOn(Notification.prototype,'_request2api');
    await this.model.disable('some-repo-id');
    let url = this.model._request2api.calls.allArgs()[0][1];
    let method = this.model._request2api.calls.allArgs()[0][0];
    let expected_url = this.model._api_url + 'notif/some-repo-id';
    expect(url).toEqual(expected_url);
    expect(method).toEqual('delete');
  });

  it('test-update', async function(){
    spyOn(Notification.prototype,'_request2api');
    await this.model.update('some-repo-id', {'field': 'val'});
    let url = this.model._request2api.calls.allArgs()[0][1];
    let method = this.model._request2api.calls.allArgs()[0][0];
    let expected_url = this.model._api_url + 'notif/some-repo-id';
    expect(url).toEqual(expected_url);
    expect(method).toEqual('put');
  });

  it('test-getIcon', function(){
    let url = this.model.getIcon();
    let expected = window.STATIC_URL + 'toxicbuild/img/notif.png';
    expect(url).toEqual(expected);
  });

});


describe('NotificationConfigViewTest', function(){

  beforeEach(function(){
    this.view = new NotificationConfigView();
  });

  it('test-getFields', function(){
    this.view.model.set('name', 'bla');
    this.view.model.set('pretty_name', 'Bla');
    this.view.model.set('something', {'pretty_name': 'Some nice thing',
				      'name': 'something',
				      '_bla': 'ble',
				      'type': 'string'});
    this.view.model.set('otherthing', {'pretty_name': '',
				       'name': 'something'});

    this.view.model.set('otherthing', {'pretty_name': 'Hi there',
				       'name': '_me'});

    let fields = this.view._getFields();
    let expected = {'Some nice thing': {name: 'something',
					required: false,
					value: '',
					'type': 'string'}};
    expect(fields).toEqual(expected);
  });

  it('test-checkChanges-ok', function(){
    affix('#notificationModal');
    let container = $('#notificationModal');
    container.affix('#btn-enable-notification');
    let first = container.affix('input');
    first.prop('required', true);
    first.val('bla');

    this.view._checkChanges();
    let btn = $('#btn-enable-notification');
    expect(btn.prop('disabled')).toBe(false);
  });

  it('test-checkChanges-not-ok', function(){
    affix('#notificationModal');
    let container = $('#notificationModal');
    container.affix('#btn-enable-notification');
    let first = container.affix('input');
    first.prop('required', true);
    first.val('');

    this.view._checkChanges();
    let btn = $('#btn-enable-notification');
    expect(btn.prop('disabled')).toBe(true);
  });

  it('test-parseValue-list', function(){
    let val = 'some, thing';
    let expected = ['some', 'thing'];
    let type = 'list';
    let returned = this.view._parseValue(val, type);
    expect(returned).toEqual(returned);
  });

  it('test-parseValue-string', function(){
    let val = 'something';
    let type = 'string';
    let returned = this.view._parseValue(val, type);
    expect(returned).toEqual(val);
  });

  it('test-getSaveData', function(){
    affix('#notificationModal');
    let container = $('#notificationModal');
    container.affix('#btn-enable-notification');
    let first = container.affix('input');
    first.prop('required', true);
    first.val('bla');
    first.prop('id', 'id-first');
    let second = container.affix('input');
    second.val('ble');
    second.prop('id', 'id-second');


    this.view.model.set('something', {'pretty_name': 'Some nice thing',
				      'name': 'first',
				      'value': '',
				      'type': 'string'});

    this.view.model.set('otherthing', {'pretty_name': 'The other stuff',
				       'name': 'second',
				       'value': '',
				       'type': 'string'});

    let expected = {'first': 'bla',
		    'second': 'ble'};
    let returned = this.view._getSaveData();
    expect(returned).toEqual(expected);
  });

  it('test-saveNotification-enable', async function(){
    spyOn(this.view.model, 'enable');
    spyOn(this.view, '_getSaveData');
    this.view.model.set('enabled', false);
    await this.view.saveNotification();
    expect(this.view.model.enable).toHaveBeenCalled();
  });

  it('test-saveNotification-update', async function(){
    spyOn(this.view.model, 'update');
    spyOn(this.view, '_getSaveData');
    this.view.model.set('enabled', true);
    await this.view.saveNotification();
    expect(this.view.model.update).toHaveBeenCalled();
  });

  it('test-mergeSaveData', function(){
    this.view.model.set('something', {'pretty_name': 'Some nice thing',
				      'name': 'first',
				      'value': '',
				      'type': 'string'});
    let data = {'first': 'bla'};
    this.view._mergeSaveData(data, true);
    let field = this.view.model.get('something');
    expect(field.value).toEqual('bla');
    expect(this.view.model.get('enabled')).toBe(true);
  });

});

describe('NotificationInfoViewTest', function(){

  beforeEach(function(){
    affix('.template .notification-item');
    let container = $('.notification-item');
    container.affix('.notification-pretty-name');
    container.affix('img.notification-img');
    container.affix('.fa-check');
    container.affix('.notification-cid');
    this.view = new NotificationInfoView();
  });

  it('test-getRendered-enabled', function(){
    spyOn(this.view, '_get_kw').and.returnValue({enabled: true});
    spyOn($.fn, 'show');
    let rendered = this.view.getRendered();
    let check = $('.fa-check', rendered);
    expect($.fn.show).toHaveBeenCalled();
  });

  it('test-getRendered-not-enabled', function(){
    spyOn(this.view, '_get_kw').and.returnValue({enabled: false});
    spyOn($.fn, 'hide');
    let rendered = this.view.getRendered();
    let check = $('.fa-check', rendered);
    expect($.fn.hide).toHaveBeenCalled();
  });

});
