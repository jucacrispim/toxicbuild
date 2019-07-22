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

describe('StreamConsumerTest', function(){

  beforeEach(function(){
    this.consumer = new StreamConsumer();
  });

  it('test-connectTo', function(){
    spyOn(window, 'WebSocket');
    this.consumer.connectTo('repo-status');
    expect(window.WebSocket).toHaveBeenCalled();
  });

  it('test-disconnect', function(){
    spyOn(this.consumer, 'ws');
    this.consumer.ws.readyState = 1;
    this.consumer.ws.close = jasmine.createSpy();
    this.consumer.disconnect();
    expect(this.consumer.ws.close).toHaveBeenCalled();
  });

  it('test-disconnect-not-connected', function(){
    spyOn(this.consumer, 'ws');
    this.consumer.ws.readyState = 3;
    this.consumer.ws.close = jasmine.createSpy();
    this.consumer.disconnect();
    expect(this.consumer.ws.close).not.toHaveBeenCalled();
  });

  it('test-handleMessage', async function(){
    let event = jasmine.createSpy('event');
    event.data = JSON.stringify({'event_type': 'repo_status_changed'});
    this.consumer.connectTo('repo-status');
    let called = false;
    $(document).unbind('repo_status_changed');
    $(document).on('repo_status_changed', function(e, msg){
      called = true;
    });
    this.consumer.handleMessage(event);
    expect(called).toBe(true);
  });
});
