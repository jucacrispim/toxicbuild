// Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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

class Slave extends BaseModel{

  constructor(){
    let api_url = window.TOXIC_API_URL + '/slave/';
    super(api_url);
  }

  static async get(kw){
    let r = await super.get(Slave, kw);
    return r;
  }

  static async list(kw){
    let r = await super.list(Slave, kw);
    return r;
  }

}
