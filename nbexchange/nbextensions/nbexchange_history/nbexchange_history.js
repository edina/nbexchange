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
    console.log(ajax);
    // Notebook v4.3.1 enabled xsrf so use notebooks ajax that includes the
    // xsrf token in the header data

    // This is the overarching "course per block" bit
    // each block then calls a routine to make the assignments & actions
    var CourseList = function (history_root_selector, refresh_selector, options) {
        this.history_root_selector = history_root_selector;
        console.log(history_root_selector);
        this.refresh_selector = refresh_selector;
        console.log(refresh_selector);

        this.history_root_selector = $(history_root_selector);
        this.refresh_element = $(refresh_selector);
        console.log(this.refresh_element);

        this.bind_events()

        options = options || {};
        this.options = options;
        console.log(options);
        this.base_url = options.base_url || utils.get_body_data("baseUrl");

        this.data = undefined;
    };

    // Remove all 'div' elements under the #history_list element
    CourseList.prototype.clear_list = function (loading) {
         $('#history_list').children('article').remove();
         var foo = this.history_root_selector;
    };

    CourseList.prototype.bind_events = function () {
        var that = this;
        this.refresh_element.click(function () {
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
        console.log(callback);
        this.callback = callback;
        this.clear_list(true);
        var settings = {
            cache : false,
            type : "GET",
            dataType : "json",
            success : $.proxy(this.handle_load_list, this),
            error : utils.log_ajax_error,
        };
        console.log(this.base_url)
        var url = utils.url_path_join(this.base_url, 'history');
        ajax(url, settings);
    };

    // Not sure what to do with this yet - I need to consider
    // showing errors
    CourseList.prototype.show_error = function (error) {
        var elems = [this.assignment_element];
        var i;

    };

    CourseList.prototype.handle_load_list = function (data, status, xhr) {
        if (data.success) {
            console.log("CourseList.prototype.handle_load_list called")
            this.load_list_success(data.value);
        } else {
            this.show_error(data.value);
        }
    };

    CourseList.prototype.load_list_success = function (data) {
        this.clear_list();
        $('#nbexchange-history_box_loading').attr("style", "display: none;");
        data.sort(function(a,b) {
            if (a.course_code < b.course_code) {
                return -1;
            } else if (a.course_code > b.course_code) {
                return 1;
            }
            return 0;
        });
        var len = data.length;
        console.log(data);

        // make the list of course boxes
        if (len==0) {
            $('#nbexchange-history_box_placeholder').attr("style", "");
        } else {
            for (var i=0; i<len; i++) {
                console.log("ADDING DIV TO PAGE")
                var element = $('<article/>');

                console.log(element);
                var item = new Course(element, data[i], this.history_root_selector,
                                        $.proxy(this.handle_load_list, this),
                                        this.options);
                this.history_root_selector.append(element);
                $("#history_list").append(element);
            }
            console.log("TOTAL history_root_selector thingies:")
            console.log(this.history_root_selector)
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
        console.log("COURSE DATA ===");
        console.log(data);
        this.parent = parent;
        this.on_refresh = on_refresh;
        this.options = options;
        this.base_url = options.base_url || utils.get_body_data("baseUrl");
        //this.style();
        this.make_box(element);
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

    Course.prototype.make_box = function (element) {
        var title_text = this.data.course_title;
        if (this.data.isInstructor) {
            title_text += ' (Instructor)'
        };
        var id = this.escape_id() + '_history_box';
        this.element = $(element);

        var title = $('<h3/>')
            .text(title_text);

        var panel_body = $('<section/>')
        
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
                var userRole = this.data.role
                var userId = this.data.user_id
                var item = new History(assignment_element, this.data.assignments[i], id,
                                        this.options, userRole, userId);
                content.append(assignment_element);
            }
        };
    };

    var History = function (assignment_element, assignment_data, parent_id, options, userRole=null, userId=null) {
        this.assignment_element = $(assignment_element);
        this.assignment_data = assignment_data;
        this.userRole = userRole;
        this.userId = userId;
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

    History.prototype.make_row = function () {

        var row = $('<div/>').addClass('col-md-12');
        var link = this.make_link();
        row.append(link);
        var summary_text_list = [];
        var summary_text = '';

        console.log("assigment data: ");
        console.log(this.assignment_data);

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
        this.assignment_data.actions.sort(function(a,b) {
            return a.timestamp - b.timestamp;
        });
        if (this.assignment_data.actions.length > 0) {
            children.append($('<tr/>')).append($('<td style="width:33%"/>').text('Timestamp')).append($('<td style="width:33%"/>').text('Action')).append($('<td style="width:33%"/>').text('User'));
        }
        for (var i=0; i<this.assignment_data.actions.length; i++) {
            console.log("ACTION USER: " );
            console.log(this.assignment_data.actions[i].user);
            console.log("THIS USER: ");
            console.log(this.userId);
            //if (this.assignment_data.actions[i].user == this.userId) {
                var action_timestamp = this.assignment_data.actions[i].timestamp.replace(/\.\d+$/, '')
                var action_text = this.assignment_data.actions[i].action.replace('AssignmentActions.', '');

                var element = $('<tr/>').append(
                    $('<td/>').text(action_timestamp)
                    ).append(
                        $('<td/>').text(action_text)
                    ).append(
                        $('<td/>').text(this.assignment_data.actions[i].user)
                    );
                children.append(element);
            //}
        }
        this.assignment_element.empty().append(row).append(children);

    };

    History.prototype.make_link = function () {
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
