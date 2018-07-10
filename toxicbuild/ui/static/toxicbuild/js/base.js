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

function _get_url(method, obj, get_with_id=true){
  let url = obj.get('url');
  if (method == 'delete' || method == 'update' ||
      (get_with_id && method == 'read')){
    url += '?id=' + obj.id;
  }
  return url;
};

class BaseModel extends Backbone.Model{

  sync(method, model, options){
    let url = _get_url(method, this);
    options.url = url;
    return super.sync(method, model, options);
  }
}


class BaseCollection extends Backbone.Collection{

  parse(data){
    return data.items;
  }
}
