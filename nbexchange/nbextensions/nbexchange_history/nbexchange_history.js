// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

define([
    'base/js/namespace',
    'jquery',
    'base/js/utils',
    'base/js/dialog',
], function(Jupyter, $, utils, dialog) {
    "use strict";

    var ajax = utils.ajax || $.ajax;
    // Notebook v4.3.1 enabled xsrf so use notebooks ajax that includes the
    // xsrf token in the header data

    // This is the overarching "course per block" bit
    // each block then calls a routine to make the assignments & actions
    // history_root_selector == <div id="history_list" class="panel-group"></div>
    var CourseList = function (history_root_selector, refresh_selector, options) {
        this.history_root_selector = history_root_selector;
        this.refresh_selector = refresh_selector;

        this.history_root_selector = $(history_root_selector);
        this.refresh_element = $(refresh_selector);

        this.bind_events()

        options = options || {};
        this.options = options;
        this.base_url = options.base_url || utils.get_body_data("baseUrl");

        this.data = undefined;
    };

    CourseList.prototype.bind_events = function () {
        var that = this;
        this.refresh_element.click(function () {
            // that.load_list();
            this.clear_list(true);
            var settings = {
                cache : false,
                type : "GET",
                dataType : "json",
                success : $.proxy(this.handle_load_list, this),
                error : utils.log_ajax_error,
            };
            var url = utils.url_path_join(this.base_url, 'history');
            ajax(url, settings);
        });
    };


    CourseList.prototype.enable_list = function () {
        this.dropdown_element.removeAttr("disabled");
    };


    CourseList.prototype.disable_list = function () {
        this.dropdown_element.attr("disabled", "disabled");
    };

    CourseList.prototype.load_list = function (callback) {
        this.callback = callback;
        this.clear_list(true);
        var settings = {
            cache : false,
            type : "GET",
            dataType : "json",
            success : $.proxy(this.handle_load_list, this),
            error : utils.log_ajax_error,
        };
        var url = utils.url_path_join(this.base_url, 'history');
        ajax(url, settings);
    };

    CourseList.prototype.clear_list = function (loading) {
        var elems = [this.assignment_element];
        var i;

    };

    CourseList.prototype.show_error = function (error) {
        var elems = [this.assignment_element];
        var i;

    };

    CourseList.prototype.handle_load_list = function (data, status, xhr) {
        if (data.success) {
            this.load_list_success(data.value);
        } else {
            this.show_error(data.value);
        }
    };

    CourseList.prototype.load_list_success = function (data) {
        this.clear_list();
        $('#nbexchange-history_box_loading').attr("style", "display: none;");
        var len = data.length;
        // make the list of course boxes
        if (len==0) {
            $('#nbexchange-history_box_placeholder').attr("style", "");
        } else {
            for (var i=0; i<len; i++) {
                var element = $('<div/>');
                var item = new Course(element, data[i], this.history_root_selector,
                                        $.proxy(this.handle_load_list, this),
                                        this.options);
                this.history_root_selector.append(element);
            }
        };

        // Add collapse arrows to links created in History.prototype.make_link
        $('.history-assignment-link').each(function(index, el) {
            var $link = $(el);
            var $icon = $('<i />')
                .addClass('fa fa-caret-down')
                .css('transform', 'rotate(-90deg)')
                .css('borderSpacing', '90')
                .css('margin-left', '3px');
            $link.append($icon);
            $link.down = false;
            $link.click(function () {
                if ($link.down) {
                    $link.down = false;
                    // jQeury doesn't know how to animate rotations.  Abuse
                    // jQueries animate function by using an unused css attribute
                    // to do the animation (borderSpacing).
                    $icon.animate({ borderSpacing: 90 }, {
                        step: function(now,fx) {
                            $icon.css('transform','rotate(-' + now + 'deg)');
                        }
                    }, 250);
                } else {
                    $link.down = true;
                    // See comment above.
                    $icon.animate({ borderSpacing: 0 }, {
                        step: function(now,fx) {
                            $icon.css('transform','rotate(-' + now + 'deg)');
                        }
                    }, 250);
                }
            });
        });

        if (this.callback) {
            this.callback();
            this.callback = undefined;
        }
    };

    var Course = function (element, data, parent, on_refresh, options) {
        this.element = $(element);
        this.data = data;
        this.parent = parent;
        this.on_refresh = on_refresh;
        this.options = options;
        this.base_url = options.base_url || utils.get_body_data("baseUrl");
        this.style();
        this.make_box(element);
    };

    Course.prototype.style = function () {
        this.element.addClass('panel').addClass("panel-default");
    };

    Course.prototype.escape_id = function () {
        // construct the id from the course id, and also prepend the id with
        // "nbexcghange" (this also ensures that the first character is always
        // a letter, as required by HTML 4)
        var id = "nbexchange-" + this.data.course_id;

        // replace spaces with '_'
        id = id.replace(/ /g, "_");

        // remove any characters that are invalid in HTML div ids
        id = id.replace(/[^A-Za-z0-9\-_]/g, "");
        return id;
    };

    // <div class="panel panel-default">
    //   <div class="panel-heading">
    //     Downloaded assignments
    //   </div>
    //   <div class="panel-body">
    //     <div id="nbexchange-$course_code_history_box" class="list_container" role="tablist" aria-multiselectable="true">
    //       <!-- assignment row -->
    //   </div>
    // </div>
    Course.prototype.make_box = function (element) {
        var title_text = this.data.course_title;
        if (this.data.isInstructor) {
            title_text += ' (Instructor)'
        };
        var id = this.escape_id() + '_history_box';
        this.element = $(element);

        var title = $('<div/>')
            .addClass('panel-heading')
            .text(title_text);
        // <div class="panel-body">
        //   <div id="$course_code_history_box" class="list_container" role="tablist" aria-multiselectable="true">
        // </div>
        var panel_body = $('<div/>')
            .addClass('panel-body');
        
        var content = ($('<div/>')
            .attr("id", id)
            .addClass("list_container")
            .attr("role", "tablist")
            .attr("aria-multiselectable", "true")
        );
        panel_body.append(content);
        element.append(title);
        element.append(panel_body);

        var len = this.data.assignments.length;

        // make the list of assignments
        if (len == 0) {
            var assignment_element = $('<p/>').text('No assignments found for this course');
            content.append(assignment_element);
        } else {
            for (var i=0; i<len; i++) {
                var assignment_element = $('<div/>');
                var item = new History(assignment_element, this.data.assignments[i], id,
                                        this.options);
                content.append(assignment_element);
            }
        };
    };

    var History = function (assignment_element, assignment_data, parent_id, options) {
        this.assignment_element = $(assignment_element);
        this.assignment_data = assignment_data;
        this.parent_id = parent_id;
        this.options = options;
        this.base_url = options.base_url || utils.get_body_data("baseUrl");
        this.style();
        this.make_row(assignment_element);
    };

    History.prototype.style = function () {
        this.assignment_element.addClass('list_item').addClass("row");
    };

    History.prototype.escape_id = function () {
        // construct the id from the course id and the assignment id, and also
        // prepend the id with "nbgrader" (this also ensures that the first
        // character is always a letter, as required by HTML 4)
        var id = "nbexchange-assignment-" + this.assignment_data.assignment_id;

        // replace spaces with '_'
        id = id.replace(/ /g, "_");

        // remove any characters that are invalid in HTML div ids
        id = id.replace(/[^A-Za-z0-9\-_]/g, "");

        return id;
    };

    // <div class="list_item row">
    //     <!-- make_row kicks in here -->
    //     <!-- This is normally-displayed div: assignment-name arrow <-> assignment <-> [submit] -->
    //     <div class="col-md-12">
    //         <span class="item_name col-sm-6">
    //             <!-- parent is div inside div#body-panel -->
    //             <!-- aria-controls is id of folded-open div -->
    //             <!-- href is id selector that aria-controls refers to -->
    //             <a class="collapsed assignment-notebooks-link" role="button" data-toggle="collapse" data-parent="#fetched_assignments_list" href="#nbgrader-made_up-1501-ref2" aria-expanded="false" aria-controls="nbgrader-made_up-1501-ref2">
    //               1501-ref2
    //               <!-- i is added by external function -->
    //               <i class="fa fa-caret-down" style="transform: rotate(-90deg); margin-left: 3px;"></i>
    //             </a>
    //         </span>
    //         <span class="item_course col-sm-2">made up</span>
    //         <span class="item_status col-sm-4">
    //             <button class="btn btn-primary btn-xs">Submit</button>
    //         </span>
    //     </div>
    //     <!-- This is the normally hidden bit, listing the notebooks -->
    //     <!-- id is referred to from aria-controls & href above -->
    //     <div id="nbgrader-made_up-1501-ref2" class="panel-collapse collapse list_container assignment-notebooks" role="tabpanel">
    //         <!-- first row is always blank -->
    //         <div class="list_item row"></div>
    //         <!-- This section is repeated for each notebook -->
    //         <div class="list_item row">
    //             <div class="col-md-12">
    //                 <span class="item_name col-sm-6">
    //                     <a href="/user/1-kiz/tree/made%20up/1501-ref2/python_squares_assessment%201.ipynb" target="_blank">python_squares_assessment 1</a>
    //                 </span>
    //                 <span class="item_course col-sm-2"></span>
    //                 <span class="item_status col-sm-4">
    //                     <button class="btn btn-default btn-xs">Validate</button>
    //                 </span>
    //             </div>
    //         </div>
    //     </div>
    // </div>
    History.prototype.make_row = function () {

        var row = $('<div/>').addClass('col-md-12');
        var link = this.make_link();
        row.append(link);
        var summary_text_list = [];
        var summary_text = '';
        if (this.assignment_data.action_summary.fetched) {
            summary_text_list.push('Released:' + this.assignment_data.action_summary.released);
        };
        if (this.assignment_data.action_summary.fetched) {
            summary_text_list.push('Fetched:' + this.assignment_data.action_summary.fetched);
        };
        if (this.assignment_data.action_summary.submitted) {
            summary_text_list.push('Submitted:' + this.assignment_data.action_summary.submitted);
        };
        if (this.assignment_data.action_summary.collected) {
            summary_text_list.push('Collected:' + this.assignment_data.action_summary.collected);
        };
        if (this.assignment_data.action_summary.feedback_released) {
            summary_text_list.push('Feedback Released:' + this.assignment_data.action_summary.feedback_released);
        };
        if (this.assignment_data.action_summary.feedback_fetched) {
            summary_text_list.push('Feedback Fetched:' + this.assignment_data.action_summary.feedback_fetched);
        };
        if (summary_text_list.length) {
            summary_text = summary_text_list.join(', ');
        }
        row.append(
            $('<span/>').addClass('item_course col-sm-6').text(summary_text)
        );

        var id, children;
        // "nbexchange-assignment-" + this.assignment_data.assignment_id;
        id = this.escape_id();
        children = $('<div/>')
            .attr("id", id)
            .addClass("panel-collapse collapse list_container history-actions")
            .attr("role", "tabpanel");

        children.append($('<div/>').addClass('list_item row'));
        for (var i=0; i<this.assignment_data.actions.length; i++) {
            var action_timestamp = this.assignment_data.actions[i].timestamp.replace(/\.\d+$/, '')
            var action_text = this.assignment_data.actions[i].action.replace('AssignmentActions.', '');

            var element = $('<div/>').addClass('list_item row').append(
                $('<div/>').addClass('col_md_12')
                    .append(
                        $('<span/>').addClass('item_name col-sm-4').text('Timestamp: ' + action_timestamp)
                    ).append(
                        $('<span/>').addClass('item_course col-sm-4').text('Action: ' + action_text)
                    ).append(
                        $('<span/>').addClass('item_status col-sm-4').text('Username:' + this.assignment_data.actions[i].user)
                    )
                );
            children.append(element);
        }

        this.assignment_element.empty().append(row).append(children);

    };

    History.prototype.make_link = function () {
        var container = $('<span/>').addClass('item_name col-sm-6');

        // "nbexchange-assignment-" + this.assignment_data.assignment_id;
        var id = this.escape_id();
        var link = $('<a/>')
            .addClass("collapsed history-assignment-link")
            .attr("role", "button")
            .attr("data-toggle", "collapse")
            .attr("data-parent", '#' + this.parent_id)
            .attr("href", "#" + id)
            .attr("aria-expanded", "false")
            .attr("aria-controls", id)


        link.text(this.assignment_data.assignment_code);
        container.append(link);
        return container;
    };

    var Action = function (element, data, options) {
        this.element = $(element);
        this.data = data;
        this.options = options;
        this.base_url = options.base_url || utils.get_body_data("baseUrl");
        this.style();
        this.make_row();
    };

    Action.prototype.style = function () {
        this.element.addClass('list_item').addClass("row");
    };

    Action.prototype.escape_id = function () {
        // construct the id from the course code and the assignment id, and also
        // prepend the id with "nbgrader" (this also ensures that the first
        // character is always a letter, as required by HTML 4)
        var id = "nbgrader-" + this.data.course_id + "-" + this.data.assignment_id;

        // replace spaces with '_'
        id = id.replace(/ /g, "_");

        // remove any characters that are invalid in HTML div ids
        id = id.replace(/[^A-Za-z0-9\-_]/g, "");

        return id;
    };

    Action.prototype.make_row = function () {
        var row = $('<div/>').addClass('col-md-12');
        var link = this.make_link();
        row.append(link);
        row.append($('<span/>').addClass('item_course col-sm-2').text(this.data.course_code));

        var id, children, element, child;
        id = this.escape_id();
        children = $('<div/>')
            .attr("id", id)
            .addClass("panel-collapse collapse list_container assignment-notebooks")
            .attr("role", "tabpanel");

        children.append($('<div/>').addClass('list_item row'));
        for (var i=0; i<this.data.notebooks.length; i++) {
            element = $('<div/>');
            this.data.notebooks[i].course_id = this.data.course_id;
            this.data.notebooks[i].assignment_id = this.data.assignment_id;
            child = new Notebook(element, this.data.notebooks[i], this.options);
            children.append(element);
        }

        row.append(this.make_button());
        this.element.empty().append(row).append(children);

    };

    return {
        'Course' : Course,
        'CourseList': CourseList,
        'History': History,
        'Action': Action,
    };
});
