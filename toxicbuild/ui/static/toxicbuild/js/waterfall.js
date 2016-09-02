jQuery('#stepDetailsModal').on('show.bs.modal', function (event) {
  var button = jQuery(event.relatedTarget);
  var command = button.data('step-command');
  var output = button.data('step-output');
  var status = button.data('step-status');
  var start = button.data('step-start');
  var end = button.data('step-end');

  var modal = jQuery(this)
  modal.find('#step-command').text(command);
  modal.find('#step-output').text(output);
  modal.find('#step-status').text(status);
  modal.find('#step-start').text(start);
  modal.find('#step-end').text(end);
});

jQuery('#buildsetDetailsModal').on('show.bs.modal', function (event) {
  var button = jQuery(event.relatedTarget);
  var commit = button.data('buildset-commit');
  var author = button.data('buildset-commit-author');
  var title = button.data('buildset-commit-title');
  var created = button.data('buildset-created');
  var branch = button.data('buildset-branch');

  var modal = jQuery(this)
  modal.find('#buildset-commit').text(commit);
  modal.find('#buildset-commit-author').text(author);
  modal.find('#buildset-commit-title').text(title);
  modal.find('#buildset-created').text(created);
  modal.find('#buildset-branch').text(branch);
});

function rebuildBuildset(button){
  var named_tree = button.data('buildset-commit');
  var branch = button.data('buildset-branch');
  var url = '/api/repo/start-build';
  var repo_name = jQuery('#waterfall-repo-name').val();
  var data = {name: repo_name, named_tree: named_tree, branch: branch};
  var success_cb = function(response){
    utils.showSuccessMessage('Buildset re-scheduled.');
  };

  var error_cb = function(response){
    utils.showErrorMessage('Error re-scheduling buildset!');
  };

  utils.sendAjax('post', url, data, success_cb, error_cb);
}

jQuery('.btn-rebuild-buildset').on('click', function(event){
  var button = jQuery(this);
  rebuildBuildset(button);
});


function rebuildBuild(button){
  var named_tree = button.data('buildset-commit');
  var branch = button.data('buildset-branch');
  var builder_name = button.data('builder-name');
  var url = '/api/repo/start-build';
  var repo_name = jQuery('#waterfall-repo-name').val();
  utils.log('rebuild build for ' + repo_name);
  var data = {name: repo_name, named_tree: named_tree, branch: branch,
	      builder_name: builder_name};
  var success_cb = function(response){
    utils.showSuccessMessage('Build re-scheduled.')
  };

  var error_cb = function(response){
    utils.showErrorMessage('Error re-scheduling build!')
  };

  utils.sendAjax('post', url, data, success_cb, error_cb);
}
jQuery('.btn-rebuild-build').on('click', function(event){
  var button = jQuery(this);
  rebuildBuild(button);
});


function sticky_relocate() {
  var BUILDER_SIZE = [];
  jQuery('.builder').each(function (){
    BUILDER_SIZE.push(jQuery(this).outerWidth());
  });
  var i = 0
  jQuery('.builder').each(function(){
    var window_top = jQuery(window).scrollTop();
    var div_top = jQuery(this).offset().top;
    if (window_top >= div_top && window_top > 52){
      jQuery(this).outerWidth(BUILDER_SIZE[i]);
      jQuery(this).addClass('builder-stick');
    }
    else{
      jQuery('.builder').each(function(){
      	jQuery(this).removeClass('builder-stick');
      });

    }
    i += 1;
  });
}

jQuery(function(){
  // jQuery('.builder').each(function (){
  //   BUILDER_SIZE.push(jQuery(this).outerWidth());
  // });
  $(window).scroll(sticky_relocate);
});


var BUILDSET_TEMPLATE  = `
    <tr class="waterfall-row">
      <td class="buildsets-column">
	<ul>
	  <li class="buildset" id="buildset-{{buildset.id}}">
	    commit: {{buildset.commit8}}<br/>
	    branch: {{buildset.branch}}<br/>
	    <button type="button" class=" btn btn-default btn-rebuild btn-transparent btn-buildset-details btn-sm"
		    data-toggle="modal"
		    data-target="#buildsetDetailsModal"
		    data-dismiss="modal"
		    data-buildset-commit="{{buildset.commit}}"
		    data-buildset-branch="{{buildset.branch}}"
		    data-buildset-commit-author="{{buildset.author}}"
		    data-buildset-commit-title="{{buildset.title}}"
		    data-buildset-created="{{buildset.created}}">
	      <span data-toggle="tooltip" title="Buildset details" data-placement="right">

		<span class="glyphicon glyphicon-modal-window" aria-hidden="true"></span>
	      </span>
	    </button>

	    <span data-toggle="tooltip" title="Re-schedule buildset" data-placement="right">
	      <button type="button" class="btn btn-default btn-rebuild btn-transparent btn-rebuild-buildset btn-sm"
		      data-buildset-commit="{{buildset.commit}}"
		      data-buildset-branch="{{buildset.branch}}">

		<span class="glyphicon glyphicon-repeat" aria-hidden="true"></span>
	      </button>
	     </span>

	  </li>
	</ul>
      </td>
    </tr>
  `

var BUILD_TEMPLATE = `
<ul>
  <li class="step step-{{build.status}}" id="build-info-{{build.id}}">
    Build - {{build.status}}
    <span data-toggle="tooltip" title="Re-schedule build" data-placement="right" style="display:none" class="rebuild-icon">
      <button type="button" class="btn btn-default btn-rebuild btn-transparent btn-rebuild-build btn-sm"
        data-buildset-commit="{{buildset.commit}}"
        data-buildset-branch="{{buildset.branch}}"
        data-builder-name="{{build.builder.name}}">

        <span class="glyphicon glyphicon-repeat" aria-hidden="true"></span>
      </button>
    </span>
  </li>
</ul>
  `;

var STEP_TEMPLATE = `
	  <li class="step step-{{step.status}}" id="step-{{step.uuid}}">
	    <div class="build-step-info-container">
	      {{step.name}} - {{step.status}}
	      <button type="button" class="btn btn-default btn-step-details btn-transparent btn-sm"
		      data-toggle="modal"
		      data-target="#stepDetailsModal"
		      data-dismiss="modal"
		      data-step-command="{{step.command}}"
		      data-step-output="{{step.output}}"
		      data-step-status="{{step.status}}"
		      data-step-start="{{step.started}}"
		      data-step-end="{{step.finished}}">
		<span data-toggle="tooltip" title="Step details" data-placement="right">
		  <span class="glyphicon glyphicon-modal-window" aria-hidden="true"></span>
		</span>

	      </button>
	    </div>
	  </li>
`

var BUILDERS = [];

function WaterfallManager(){
  obj = {
    url: 'ws://' + window.location.host + '/api/socks/builds',
    ws: null,

    init: function(){
      var self = this;
      self.ws = new WebSocket(self.url);
      self.ws.onmessage = function(event){
	self.handleEvent(self, event);
      };
    },

    handleEvent: function(self, event){

      var data = jQuery.parseJSON(event.data);
      if (data.event_type == 'build_added'){
	self.handleBuildAdded(data);
      }else if (data.event_type == 'build_started'){
	self.handleBuildStarted(data);
      }else if (data.event_type == 'build_finished'){
	self.handleBuildFinished(data);
      }else if (data.event_type == 'step_started'){
	self.handleStepStarted(data);
      }else if (data.event_type == 'step_finished'){
	self.handleStepFinished(data);
      }
    },

    handleStepStarted: function(step){
      var self = this;

      var template = STEP_TEMPLATE.replace(/{{step.uuid}}/g, step.uuid);
      template = template.replace(/{{step.status}}/g, step.status);
      template = template.replace(/{{step.name}}/g, step.name);
      template = template.replace(/{{step.command}}/g, step.command);
      template = template.replace(/{{step.output}}/g, step.output);
      template = template.replace(/{{step.started}}/g, step.started);
      template = template.replace(/{{step.finished}}/g, step.finished);

      var build = step.build
      var build_el = jQuery('#build-info-' + build.uuid);
      build_el.parent().append(template);
    },

    handleStepFinished: function(step){
      var self = this;

      var step_el = jQuery('#step-' + step.uuid);
      var html = step_el.html();
      step_el.removeClass('step-running').addClass('step-' + step.status);
      html = html.replace(step.status, step.status);
      html = html.replace(step.output, step.output);
      html = html.replace(step.finished, step.finished);
      step_el.html(html);
    },

    handleBuildStarted: function(build){
      var self = this;

      var build_el = jQuery('#build-info-' + build.uuid);
      build_el.html(build_el.html().replace(/pending/, 'running'));
      build_el.removeClass('step-pending').addClass('step-running');

      var builder_input = jQuery('#builder-' + build.builder.id)
      var builder_status = builder_input.val();
      if (builder_status != 'running'){
	builder_input.parent().removeClass('builder-' + builder_status);
	builder_input.parent().addClass('builder-running');
      }
    },

    handleBuildFinished: function(build){
      var self = this;

      var build_el = jQuery('#build-info-' + build.uuid);
      build_el.html(build_el.html().replace(/running/, build.status));
      jQuery('.rebuild-icon', build_el).show();

      jQuery('.btn-rebuild-build', build_el).on('click', function(event){
	var button = jQuery(this);
	rebuildBuild(button);
      });

      build_el.removeClass('step-running').addClass('step-' + build.status);
      var builder_input = jQuery('#builder-' + build.builder.id)
      var builder_status = builder_input.val();
      if (builder_status != 'running'){
	builder_input.parent().removeClass('builder-running');
	builder_input.parent().addClass('builder-' + builder_status);
      }

    },

    handleBuildAdded: function(build){
      var self = this;
      var buildset = build.buildset;
      var buildset_li = jQuery('#buildset-' + buildset.id);
      if (!buildset_li.length){
	self._addBuildSet(buildset);
      };
      self._addBuild(build);

    },

    _addBuildSet: function(buildset){
      var self = this;

      var template = BUILDSET_TEMPLATE.replace(/{{buildset.id}}/g, buildset.id);
      template = template.replace(/{{buildset.commit}}/g, buildset.commit);
      template = template.replace(/{{buildset.commit8}}/g, buildset.commit.slice(0, 8));
      template = template.replace(/{{buildset.author}}/g, buildset.author);
      template = template.replace(/{{buildset.branch}}/g, buildset.branch);
      template = template.replace(/{{buildset.title}}/g, buildset.title);
      template = template.replace(/{{buildset.created}}/g, buildset.created);
      var first_row = jQuery('#waterfall-first-row');
      jQuery(template).insertAfter(first_row);

      var buildset_el = jQuery('#buildset-' + buildset.id).parent().parent().parent();
      for (i = 0; i < buildset.builds.length; i++){
	var builder = BUILDERS[i];
	try{
	  var parsed_builder = jQuery.parseJSON(builder);
	  builder = parsed_builder;
	}catch (e){
	  utils.log(e);
	  utils.log(BUILDERS[i]);
	};

	buildset_el.append('<td class="builder-column" id="build-builder-'+ builder.id +'"></td>');
      };

      jQuery('.btn-rebuild-buildset', buildset_el).on('click', function(event){
	var button = jQuery(this);
	rebuildBuildset(button);
      });


    },

    _addBuild: function(build){
      var self = this;
      var builder = self._getBuilder(build.builder.id);
      var buildset = build.buildset
      var build_el = jQuery('#build-builder-' + build.builder.id);
      var template = BUILD_TEMPLATE.replace(/{{build.status}}/g, build.status);
      template = template.replace(/{{buildset.commit}}/g, buildset.commit);
      template = template.replace(/{{build.id}}/g, build.uuid);
      template = template.replace(/{{buildset.branch}}/g, buildset.branch);
      utils.log(builder);
      template = template.replace(/{{build.builder.name}}/g, builder.name);
      jQuery(build_el).append(template);


    },

    _getBuilder: function(builder_id){
      for (i = 0; i < BUILDERS.length; i++){
	var builder = jQuery.parseJSON(BUILDERS[i]);
	if (builder_id == builder.id){
	  return builder;
	};
      };
    },
  };

  obj.init();
  return obj;
};

var manager = WaterfallManager();
