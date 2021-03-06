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


class Terminal {

  constructor(container){
    this.el = container;
    this.ansi_up = new AnsiUp;
    this.clean();
  }

  write(content){
    let c = this.ansi_up.ansi_to_html(content);
    this.el.innerHTML += c;
  }

  readAll(){
    return this.el.innerHTML;
  }

  clean(){
    this.el.innerHTML = '';
  }
}
