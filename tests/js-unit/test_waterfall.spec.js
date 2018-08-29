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

describe('WaterfallTest', function(){

  beforeEach(function(){
    this.waterfall = new Waterfall();
    spyOn($, 'ajax');
  });

  it('test-fetch', async function(){
    $.ajax.and.returnValue({buildsets: [{}],
			    builders: [{}]});
    await this.waterfall.fetch();
    expect(this.waterfall.buildsets.length).toEqual(1);
    expect(this.waterfall.builders.length).toEqual(1);
  });
});

describe('WaterfallBuilderViewTest', function(){

  beforeEach(function(){
    affix('.template .waterfall-tr');
    let template = $('.waterfall-tr');
    template.affix('.builder-name');
    let builder = new Builder();
    this.view = new WaterfallBuilderView({builder: builder});
  });

  it('test-constructor-without-buildset', function(){

    expect(function(){new WaterfallBuilderView();}).toThrow(
      new Error('You must pass a builder'));
  });

  it('test-getRendered', function(){
    let r = this.view.getRendered();
    expect(Boolean(r.length)).toBe(true);
  });

});


describe('WaterfallViewTest', function(){

  beforeEach(function(){
    affix('#waterfall-header');
    affix('.template .waterfall-tr');
    let template = $('.waterfall-tr');
    template.affix('.builder-name');

    this.view = new WaterfallView('some/repo');
  });

  it('test-renderHeader', function(){
    this.view.model.builders.add({'name': 'bla'});
    let header = this.view._renderHeader();
    expect(header.length).toEqual(1);
  });

  it('test-render', async function(){
    spyOn(this.view.model, 'fetch');
    spyOn(this.view, '_renderHeader').and.returnValue('bla');
    await this.view.render();
    let header_container = $('#waterfall-header');
    let header = header_container.html();
    expect(header).toEqual('bla');
  });

});
