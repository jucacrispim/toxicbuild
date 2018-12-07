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

describe('loadTranslationsTest', function(){

  it('test-no-language-cookie', async function(){
    spyOn(Cookies, 'get').and.returnValue(null);
    let r = await utils.loadTranslations();
    expect(r).toBe(false);
  });

  it('test-locale-en-us', async function(){
    spyOn(Cookies, 'get').and.returnValue('en_US');
    spyOn(i18n.translator, 'reset');
    let r = await utils.loadTranslations();
    expect(r).toBe(true);
    expect(i18n.translator.reset).toHaveBeenCalled();
  });

  it('test-bad-request', async function(){
    spyOn(Cookies, 'get').and.returnValue('pt_BR');
    spyOn($, 'ajax').and.throwError();
    let r = await utils.loadTranslations();
    expect(r).toBe(false);
  });

  it('test-ok', async function(){
    spyOn(Cookies, 'get').and.returnValue('pt_BR');
    spyOn($, 'ajax');
    spyOn(JSON, 'parse');
    spyOn(i18n.translator, 'add');
    let r = await utils.loadTranslations();
    expect(r).toBe(true);
    expect(i18n.translator.add).toHaveBeenCalled();
  });

});

describe('TimeCounterTest', function(){

  beforeEach(function(){
    this.counter = new TimeCounter();
  });

  it('test-stop', function(){
    this.counter.stop();
    expect(this.counter._stop).toBe(true);
  });

  it('test-start', function(){
    let self = this;

    spyOn(utils, 'sleep');
    let cb = function(secs){self.counter._stop = true;};

    this.counter.start(cb);
    expect(utils.sleep).toHaveBeenCalled();
  });
});


describe('utilsTest', function(){

  it('test-formatSeconds', function(){
    let secs = 75;
    let formated = utils.formatSeconds(secs);
    expect(formated).toEqual('00:01:15');
  });

  it('test-setTZCookie', function(){
    spyOn(utils, 'getClientTZ');
    spyOn(Cookies, 'set');

    utils.setTZCookie();
    expect(Cookies.set).toHaveBeenCalled();
  });

  it('test-getClientTZ-ok', function(){
    let e = Intl.DateTimeFormat().resolvedOptions().timeZone;
    let r = utils.getClientTZ();
    expect(r).toEqual(e);
  });

  it('test-getClientTZ-error', function(){
    spyOn(Intl, 'DateTimeFormat').and.throwError();
    let e = 'UTC';
    let r = utils.getClientTZ();
    expect(r).toEqual(e);
  });
});
