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

describe('BuildsetInfoViewTest', function(){

  beforeEach(function(){
    affix('.template .buildset-info');
    let container = $('.buildset-info');
    container.affix('.buildset-title');
    container.affix('.buildset-branch');
    container.affix('.buildset-status');
    container.affix('.buildset-commit');
    container.affix('.buildset-commit-date');
    container.affix('.buildset-started');
    container.affix('.buildset-total-time');
    this.view = new BuildSetInfoView();
  });

  it('test-getRendered-not-started', function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail',
						 started: null});
    spyOn($.fn, 'show');
    this.view.getRendered();
    expect($.fn.show).not.toHaveBeenCalled();
  });

  it('test-getRendered-started', function(){
    spyOn(this.view, '_get_kw').and.returnValue({status: 'fail',
						 started: 'some str datetime'});

    spyOn($.fn, 'show');
    this.view.getRendered();
    expect($.fn.show).toHaveBeenCalled();
  });
});


describe('BuildSetListViewTest', function(){

  beforeEach(function(){
    affix('.template .buildset-info');
    let container = $('.buildset-info');
    container.affix('.buildset-title');
    container.affix('.buildset-branch');
    container.affix('.buildset-status');
    container.affix('.buildset-commit');
    container.affix('.buildset-commit-date');
    container.affix('.buildset-started');
    container.affix('.buildset-total-time');

    this.view = new BuildSetListView('some/repo');
  });

  it('test-get_view', function(){
    let view = this.view._get_view();
    expect(view instanceof BuildSetInfoView).toBe(true);
  });
});
