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
});
