// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

define([
    'base/js/namespace',
    'jquery',
    'base/js/utils',
    'base/js/dialog',
], function(Jupyter, $, utils, dialog) {
    "use strict";
    console.log("CLIENT - first function");
    var ajax = utils.ajax || $.ajax;
    // Notebook v4.3.1 enabled xsrf so use notebooks ajax that includes the
    // xsrf token in the header data

    // This is the overarching "course per block" bit
    // each block then calls a routine to make the assignments & actions
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

    // Remove all 'div' elements under the #history_list element
    CourseList.prototype.clear_list = function (loading) {
        // this.history_root_selector.children('div').remove
        // var foo = this.history_root_selector;
    };

    CourseList.prototype.bind_events = function () {
        var that = this;
        this.refresh_element.click(function () {
            console.log("CLIENT - Refresh clicked")
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
        console.log("CLIENT - Enable list")
        this.dropdown_element.removeAttr("disabled");
    };


    CourseList.prototype.disable_list = function () {
        console.log("CLIENT - Disable list")
        this.dropdown_element.attr("disabled", "disabled");
    };

    CourseList.prototype.load_list = function (callback) {
        console.log("CLIENT - Load list")
        console.log("CLIENT - Callback:")
        console.log(callback)
        this.callback = callback;
        console.log("CLIENT - [Before] Clear List")
        this.clear_list(true);
        console.log("CLIENT - Set settings")
        var settings = {
            cache : false,
            type : "GET",
            dataType : "json",
            success : $.proxy(this.handle_load_list, this),
            error : utils.log_ajax_error,
        };
        console.log("CLIENT - Done settings")
        console.log("CLIENT - Base URL:")
        console.log(this.base_url)
        var url = utils.url_path_join(this.base_url, 'history');
        console.log("CLIENT - Set url")
        console.log("CLIENT - Start AJAX")
        ajax(url, settings);
    };

    // Not sure what to do with this yet - I need to consider
    // showing errors
    CourseList.prototype.show_error = function (error) {
        console.log("CLIENT - Show Error")
        var elems = [this.assignment_element];
        var i;

    };

    CourseList.prototype.handle_load_list = function (data, status, xhr) {
        console.log("CLIENT - Handle load list")
        if (data.success) {
            this.load_list_success(data.value);
        } else {
            this.show_error(data.value);
        }
    };

    CourseList.prototype.load_list_success = function (data) {
        console.log("CLIENT - Load list list")
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
            console.log("CLIENT - Add collapse arror")
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
        console.log("CLIENT - Style")
        this.element.addClass('panel').addClass("panel-default");
    };

    Course.prototype.escape_id = function () {
        console.log("CLIENT - Escape ID")
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

    Course.prototype.make_box = function (element) {
        console.log("CLIENT - prototype Make box")
        var title_text = this.data.course_title;
        if (this.data.isInstructor) {
            title_text += ' (Instructor)'
        };
        var id = this.escape_id() + '_history_box';
        this.element = $(element);

        var title = $('<div/>')
            .addClass('panel-heading')
            .text(title_text);

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
        console.log("CLIENT - History style")
        this.assignment_element.addClass('list_item').addClass("row");
    };

    History.prototype.escape_id = function () {
        console.log("CLIENT - Escape ID")
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

    History.prototype.make_row = function () {
        console.log("CLIENT - Make row")

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
        console.log("CLIENT - Make link")
        var container = $('<span/>').addClass('item_name col-sm-6');

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

    return {
        'Course' : Course,
        'CourseList': CourseList,
        'History': History,
    };
});
