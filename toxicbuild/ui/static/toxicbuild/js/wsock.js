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


class StreamConsumer{

  constructor(){
    this.url = 'ws://' + window.location.host + '/api/socks/';
    this.ws = null;
  }

  connectTo(action){
    let self = this;

    let url = this.url + action;
    this.ws = new WebSocket(url);
    this.ws.onmessage = function(event){
      self.handleMessage(event);
    };
  }

  disconnect(){
    if (this.ws && this.ws.readyState == 1){
      this.ws.close();
    }
  }

  handleMessage(event){
    let msg = $.parseJSON(event.data);
    let etype = msg.event_type;
    $(document).trigger(etype, msg);
  }
}
