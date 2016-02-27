var REPO_ROW_TEMPLATE = [
  '<tr id="row-{{repo.name}}">',
  '<td>',
  '<a href="javascript:showRepoModal(\'{{repo.name}}\', \'{{repo.url}}\', \'{{repo.vcs_type}}\', {{repo.update_seconds}}, {{[s.name for s in repo.slaves]}})">',
  '{{repo.name}}',
  '</a>',
  '</td>',
  '<td>{{repo.url}}</td>',
  '<td><button type="button" class="btn btn-xs btn-{{get_btn_class(repo.status)}} btn-status">{{repo.status}}</button></td>',
    '<td><button type="button" class="btn btn-xs btn-toxicbuild-default btn-status">start build</button></td>',
  '</tr>',
];

var SLAVE_ROW_TEMPLATE = [
  '<tr id="row-{{slave.name}}">',
  '<td>',
  '<a href="javascript:showSlaveModal(\'{{slave.name}}\', \'{{slave.host}}\', \'{{slave.port}}\')">',
  '{{slave.name}}',
  '</a>',
  '</td>',
  '<td>{{slave.host}}</td>',
  '<td>{{slave.port}}</td>',
  '</tr>',
];


// Repository stuff
$('#repoModal').on('hidden.bs.modal', function (event) {
  var repo_modal = $(this)
  repo_modal.find('.modal-title').text('Add repository')
  repo_modal.find('#repo_name').val('');
  repo_modal.find('#repo_url').val('');
  repo_modal.find('#repo_update_seconds').val(300);
  repo_modal.find('#repo_vcs_type').val('');
  repo_modal.find("#btn-delete-repo").hide()
});

$('#btn-delete-repo').on('click', function(){
  $('#repo-req-type').val('delete');
})

$("#repoModal").on('submit', function(event){
  // event prevented here means that the form was not considered valid.
  if (event.isDefaultPrevented()){
    return false;
  }

  event.preventDefault();

  var repo_modal = $('#repoModal');
  var name = repo_modal.find('#repo_name').val();
  var url = repo_modal.find('#repo_url').val();
  var update_seconds = repo_modal.find('#repo_update_seconds').val();
  var vcs_type = repo_modal.find('#repo_vcs_type').val();
  var slaves = new Array();
  jQuery('#repo_slaves option:selected').each(function(){
    slaves.push(this.value);
  })
  $.ajax({
    type: jQuery('#repo-req-type').val(),
    url: '/api/repo/',
    data: {'name': name, 'url': url, 'update_seconds': update_seconds,
	   'vcs_type': vcs_type, 'slaves': slaves},
    traditional: true,
    success: function(respone){
      var old_action = $('#repo-req-type').val();
      if (old_action == 'post' || old_action == 'put'){
	_insert_repo_row(name, url, vcs_type, update_seconds, slaves);
      }
      else if (old_action == 'delete'){
	_remove_repo_row(name);
      }
      $('#repo-req-type').val('post');
      repo_modal.modal('toggle');
      $('#success-message').alert()
    },
    error: function(response){
      $('#repo-req-type').val('post')
      repo_modal.modal('toggle');
      $('#error-message').alert()
    }
  })

});



function _insert_repo_row(name, url, vcs_type, update_seconds, slaves){
  //var repo_modal =
  repo_modal.modal('hide');
  $('#success-message').alert();
  var repo_row = REPO_ROW_TEMPLATE.join('').replace(/{{repo.name}}/g, name);
  repo_row = repo_row.replace(/{{repo.url}}/g, url);
  repo_row = repo_row.replace(/{{repo.vcs_type}}/g, vcs_type);
  repo_row = repo_row.replace(/{{repo.update_seconds}}/g, update_seconds);
  repo_row = repo_row.replace(/{{[s.name for s in repo.slaves]}}/g,
			      str(slaves));
  $('#tbody-repos').append(repo_row);
}

function _remove_repo_row(name){
  $('#row-' + name).remove();
}


function showRepoModal(name, url, vcs_type, update_seconds, slaves){
  var repo_modal = $('#repoModal');
  repo_modal.find('#repo-req-type').val('put');
  repo_modal.find('.modal-title').text(name);
  repo_modal.find('#repo_name').val(name);
  repo_modal.find('#repo_url').val(url);
  repo_modal.find('#repo_update_seconds').val(update_seconds);
  repo_modal.find('#repo_vcs_type').val(vcs_type);
  repo_modal.find("#btn-delete-repo").show()
  repo_modal.modal('toggle')
}


// start build stuff

$('.start-build-btn').on('click', function(event){
  $('#repo-start-build-name').val($(this).data('repo-name'));
});


$("#startBuildModal").on('submit', function(event){
  // event prevented here means that the form was not considered valid.
  if (event.isDefaultPrevented()){
    return false;
  }

  event.preventDefault();

  var repo_name = $('#repo-start-build-name').val()
  var branch = $('#branch').val();
  var builder_name = $('#builder_name').val();
  var named_tree = $('#named_tree').val();
  var slaves = new Array();
  jQuery('#repo_slaves option:selected').each(function(){
    slaves.push(this.value);
  });

  var kwargs = {'branch': branch, 'name': repo_name};
  if (builder_name){
    kwargs['builder_name'] = builder_name;
  }
  if(named_tree){
    kwargs['named_tree'] = named_tree;
  }
  if (slaves){
    kwargs['slaves'] = slaves;
  }

  $.ajax({
    type: 'post',
    url: '/api/repo/start-build',
    data: kwargs,
    traditional: true,
    success: function(response){
      var modal = $('#startBuildModal')
      var msg_container = $('#success-container')
      modal.modal('toggle');
      msg_container.text(response);
      $('.alert-success').show();
      setTimeout(function(){$('.alert-success').fadeOut()}, 5000);
    },
    error: function(response){
      console.log('deu ruim');
    }

  });
})


// slave stuff

$('#slaveModal').on('hidden.bs.modal', function (event) {
  var slave_modal = $(this)
  slave_modal.find('.modal-title').text('Add slave')
  slave_modal.find('#slave_name').val('');
  slave_modal.find('#slave_host').val('');
  slave_modal.find('#slave_port').val('');
  slave_modal.find("#btn-delete-slave").hide()
});


function showSlaveModal(name, host, port){
  var slave_modal = $('#slaveModal');
  slave_modal.find('#repo-req-type').val('put');
  slave_modal.find('.modal-title').text(name);
  slave_modal.find('#slave_name').val(name);
  slave_modal.find('#slave_host').val(host);
  slave_modal.find('#slave_port').val(port);
  slave_modal.find("#btn-delete-slave").show()
  slave_modal.modal('toggle')
}

$('#btn-delete-slave').on('click', function(){
  $('#slave-req-type').val('delete');
})


function _insert_slave_row(name, host, port){
  var slave_modal = $('#slaveModal');
  slave_modal.modal('hide');
  $('#success-message').alert();
  var slave_row = SLAVE_ROW_TEMPLATE.join('').replace(/{{slave.name}}/g, name);
  slave_row = slave_row.replace(/{{slave.host}}/g, host);
  slave_row = slave_row.replace(/{{slave.port}}/g, port);

  $('#tbody-slaves').append(slave_row);
}

$("#slaveModal").on('submit', function(event){
  // event prevented here means that the form was not considered valid.
  if (event.isDefaultPrevented()){
    return false;
  }

  event.preventDefault();

  var modal = $('#slaveModal');
  var name = modal.find('#slave_name').val();
  var host = modal.find('#slave_host').val();
  var port = modal.find('#slave_port').val();
  $.ajax({
    type: jQuery('#slave-req-type').val(),
    url: '/api/slave/',
    data: {'name': name, 'host': host, 'port': port},
    traditional: true,

    success: function(respone){
      var old_action = $('#slave-req-type').val();
      if (old_action == 'post' || old_action == 'put'){
	_insert_slave_row(name, host, port);
      }

      else if (old_action == 'delete'){
	_remove_repo_row(name);
      }

      $('#slave-req-type').val('post');
      modal.modal('hide')
      $('#success-message').alert()
    },
    error: function(response){
      $('#slave-req-type').val('post')
      modal.modal('hide');
      $('#error-message').alert()
    }
  })

});


// waterfall
$('#stepDetailsModal').on('show.bs.modal', function (event) {
  var button = $(event.relatedTarget);
  var command = button.data('step-command');
  var output = button.data('step-output');
  var status = button.data('step-status');
  var start = button.data('step-start');
  var end = button.data('step-end');

  var modal = $(this)
  modal.find('#step-command').text(command);
  modal.find('#step-output').text(output);
  modal.find('#step-status').text(status);
  modal.find('#step-start').text(start);
  modal.find('#step-end').text(end);
})
