define([
    'base/js/namespace',
    'jquery',
    'base/js/utils',
    './nbexchange_history',
    './sorttable',
], function(Jupyter, $, utils, HistoryList, sorttable) {
    "use strict";

    var ajax = utils.ajax || $.ajax;
    // Notebook v4.3.1 enabled xsrf so use notebooks ajax that includes the
    // xsrf token in the header data

    var history_html = $([
        '<div id="history" class="tab-pane">',
        '  <div id="history_toolbar" class="row list_toolbar">',
        '    <div class="col-sm-8 no-padding">',
        '      <span id="history_list_info" class="toolbar_info">History of Exchange interactions</span>',
        '    </div>',
        '    <div class="col-sm-4 no-padding tree-buttons">',
        '      <span id="history_buttons" class="pull-right toolbar_buttons">',
        '      <button id="refresh_history_list" title="Refresh history list" class="btn btn-default btn-xs"><i class="fa fa-refresh"></i></button>',
        '      </span>',
        '    </div>',
        '  </div>',
        '  <div id="nbexchange-history_box_placeholder" class="row list_placeholder" style="display: none;">',
        '    <div> There are no downloaded assignments. </div>',
        '  </div>',
        '  <div id="nbexchange-history_box_loading" class="row list_loading" >',
        '    <div> Querying the assignment exchange service. Please wait, this may take several minutes... </div>',
        '  </div>',
        '  <div id="nbexchange-history_box_error" class="row list_error" style="display: none;">',
        '    <div></div>',
        '  </div>',
        '  <div class="alert alert-danger version_error">',
        '  </div>',
        '  <div id="history_list" class="panel-group">',
        '  </div>',
        '</div>'
    ].join('\n'));

    function load() {
        var history_list = new HistoryList.CourseList(
            '#history_list',
            '#refresh_history_list',
            {
                base_url: Jupyter.notebook_list.base_url,
            }
        );
        // if (!Jupyter.notebook_list) return;
        var base_url = Jupyter.notebook_list.base_url;
        $('head').append(
            $('<link>')
            .attr('rel', 'stylesheet')
            .attr('type', 'text/css')
            .attr('href', base_url + 'nbextensions/nbexchange_history/nbexchange_history.css')
        );
        $(".tab-content").append(history_html);

        $("#tabs").append(
            $('<li>')
            .append(
                $('<a>')
                .attr('href', '#history')
                .attr('data-toggle', 'tab')
                .text('Exchange History')
                .click(function (e) {
                    window.history.pushState(null, null, '#history');
                    history_list.load_list();
                    console.log("HISTORY LIST")
                    console.log(history_list);
                })
            )
        );


    }
    return {
        
        load_ipython_extension: load
    };
});
