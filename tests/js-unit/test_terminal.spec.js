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

describe('TerminalTest', function(){

  beforeEach(function(){
    affix('#build-output');
    let el = document.getElementById('build-output');
    this.term = new Terminal(el);
  });

  it('test-write', function(){
    let txt = 'olá, mundo!';
    this.term.write(txt);
    expect(this.term.readAll()).toEqual(txt);
  });

  it('test-clean', function(){
    let txt = 'olá, mundo!';
    this.term.write(txt);
    this.term.clean();
    expect(this.term.readAll()).toEqual('');
  });
});
