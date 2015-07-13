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
      repo_modal.modal('hide')
      $('#success-message').alert()
    },
    error: function(response){
      $('#repo-req-type').val('post')
      repo_modal.modal('hide');
      $('#error-message').alert()
    }
  })

});



function _insert_repo_row(name, url, vcs_type, update_seconds, slaves){
  repo_modal.modal('hide');
  $('#success-message').alert();
  var repo_row = REPO_ROW_TEMPLATE.replace('{{repo.name}}', name);
  repo_row = repo_row.replace('{{repo.url}}', url);
  repo_row = repo_row.replace('{{repo.vcs_type}}', vcs_type);
  repo_row = repo_row.replace('{{repo.update_seconds}}', update_seconds);
  repo_row = repo_row.replace('{{[s.name for s in repo.slaves]}}',
			      str(slaves));
  $('#tbody-repos').append(repo_row);
}

function _remove_repo_row(name){
  $('#row-' + name).remove();
}

$('#repo-form').validator();


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

$('#start-build-btn').on('click', function(event){
  $('#repo-start-build-name').val($('#start-build-btn').data('repo-name'));
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
