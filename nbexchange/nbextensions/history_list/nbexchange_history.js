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

        // remove list items
        for (i = 0; i < elems.length; i++) {
            elems[i].children('.list_item').remove();
            if (loading) {
                // show loading
                elems[i].children('.list_loading').show();
                // hide placeholders and errors
                elems[i].children('.list_placeholder').hide();
                elems[i].children('.list_error').hide();

            } else {
                // show placeholders
                elems[i].children('.list_placeholder').show();
                // hide loading and errors
                elems[i].children('.list_loading').hide();
                elems[i].children('.list_error').hide();
            }
        }
    };

    CourseList.prototype.show_error = function (error) {
        var elems = [this.assignment_element];
        var i;

        // remove list items
        for (i = 0; i < elems.length; i++) {
            elems[i].children('.list_item').remove();
            // show errors
            elems[i].children('.list_error').show();
            elems[i].children('.list_error').text(error);
            // hide loading and placeholding
            elems[i].children('.list_loading').hide();
            elems[i].children('.list_placeholder').hide();
        }
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

        var len = data.length;
        // make the list of course boxes
        for (var i=0; i<len; i++) {
            var element = $('<div/>');
            var item = new Course(element, data[i], this.history_root_selector,
                                      $.proxy(this.handle_load_list, this),
                                      this.options);
            this.history_root_element.append(element);
        }


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
        this.make_box();
    };

    Course.prototype.style = function () {
        this.element.addClass('panel').addClass("panel-default");
    };

    Course.prototype.escape_id = function () {
        // construct the id from the course id, and also prepend the id with
        // "nbexcghange" (this also ensures that the first character is always
        // a letter, as required by HTML 4)
        var id = "nbexchange-" + this.data.course_code;

        // replace spaces with '_'
        id = id.replace(/ /g, "_");

        // remove any characters that are invalid in HTML div ids
        id = id.replace(/[^A-Za-z0-9\-_]/g, "");

        return id;
    };

    Course.prototype.make_box = function () {
        var title = $('<div/>')
            .addClass('panel-heading')
            .text(this.data.course_title);
        var content = $('<div/>')
            .addClass('panel-body')

        // <div id="$course_code_history_box" class="list_container" role="tablist" aria-multiselectable="true">
        id = this.escape_id() + '_history_box';
        content.append(
            $('<div/>')
            .attr("id", id)
            .addClass("list_container")
            .attr("role", "tablist")
            .attr("aria-multiselectable", "true")
        )
        this.element.append(title);
        this.element.append(content);
    };


    var History = function (element, data, parent, on_refresh, options) {
        this.element = $(element);
        this.data = data;
        this.parent = parent;
        this.on_refresh = on_refresh;
        this.options = options;
        this.base_url = options.base_url || utils.get_body_data("baseUrl");
        this.style();
        this.make_row();
    };

    History.prototype.style = function () {
        this.element.addClass('list_item').addClass("row");
    };

    History.prototype.escape_id = function () {
        // construct the id from the course id and the assignment id, and also
        // prepend the id with "nbgrader" (this also ensures that the first
        // character is always a letter, as required by HTML 4)
        var id = "nbgrader-" + this.data.course_id + "-" + this.data.assignment_id;

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
        row.append($('<span/>').addClass('item_course col-sm-2').text(this.data.course_id));

        var id, children, element, child;
        if (this.data.status === 'submitted') {
            id = this.escape_id() + "-submissions";
            children = $('<div/>')
                .attr("id", id)
                .addClass("panel-collapse list_container History-notebooks")
                .attr("role", "tabpanel");

            children.append($('<div/>').addClass('list_item row'));
            for (var i=0; i<this.data.submissions.length; i++) {
                element = $('<div/>');
                child = new Submission(element, this.data.submissions[i], this.options);
                children.append(element);
            }

        } else if (this.data.status === 'fetched') {
            id = this.escape_id();
            children = $('<div/>')
                .attr("id", id)
                .addClass("panel-collapse collapse list_container History-notebooks")
                .attr("role", "tabpanel");

            children.append($('<div/>').addClass('list_item row'));
            for (var i=0; i<this.data.notebooks.length; i++) {
                element = $('<div/>');
                this.data.notebooks[i].course_id = this.data.course_id;
                this.data.notebooks[i].History_id = this.data.History_id;
                child = new Notebook(element, this.data.notebooks[i], this.options);
                children.append(element);
            }
        }

        row.append(this.make_button());
        this.element.empty().append(row).append(children);
    };

    History.prototype.make_link = function () {
        var container = $('<span/>').addClass('item_name col-sm-6');
        var link;

        if (this.data.status === 'fetched') {
            var id = this.escape_id();
            link = $('<a/>')
                .addClass("collapsed History-notebooks-link")
                .attr("role", "button")
                .attr("data-toggle", "collapse")
                .attr("data-parent", this.parent)
                .attr("href", "#" + id)
                .attr("aria-expanded", "false")
                .attr("aria-controls", id)
        } else {
            link = $('<span/>');
        }

        link.text(this.data.History_id);
        container.append(link);
        return container;
    };

    History.prototype.submit_error = function (data) {
        var body = $('<div/>').attr('id', 'submission-message');

        body.append(
            $('<div/>').append(
                $('<p/>').text('History not submitted:')
            )
        );
        body.append(
            $('<pre/>').text(data.value)
        );

        dialog.modal({
            title: "Invalid Submission",
            body: body,
            buttons: { OK: { class : "btn-primary" } }
        });
    };

    History.prototype.make_button = function () {
        var that = this;
        var container = $('<span/>').addClass('item_status col-sm-4');
        var button = $('<button/>').addClass("btn btn-primary btn-xs");
        container.append(button);

        if (this.data.status == 'released') {
            button.text("Fetch");
            button.click(function (e) {
                var settings = {
                    cache : false,
                    data : {
                        course_id: that.data.course_id,
                        History_id: that.data.History_id
                    },
                    type : "POST",
                    dataType : "json",
                    success : $.proxy(that.on_refresh, that),
                    error : function (xhr, status, error) {
                        container.empty().text("Error fetching History.");
                        utils.log_ajax_error(xhr, status, error);
                    }
                };
                button.text('Fetching...');
                button.attr('disabled', 'disabled');
                var url = utils.url_path_join(
                    that.base_url,
                    'Historys',
                    'fetch'
                );
                ajax(url, settings);
            });

        } else if (this.data.status == 'fetched') {
            button.text("Submit");
            button.click(function (e) {
                var settings = {
                    cache : false,
                    data : {
                        course_id: that.data.course_id,
                        History_id: that.data.History_id
                    },
                    type : "POST",
                    dataType : "json",
                    success : function (data, status, xhr) {
                        if (!data.success) {
                            that.submit_error(data);
                            button.text('Submit');
                            button.removeAttr('disabled');
                        } else {
                            that.on_refresh(data, status, xhr);
                        }
                    },
                    error : function (xhr, status, error) {
                        container.empty().text("Error submitting History.");
                        utils.log_ajax_error(xhr, status, error);
                    }
                };
                button.text('Submitting...');
                button.attr('disabled', 'disabled');
                var url = utils.url_path_join(
                    that.base_url,
                    'Historys',
                    'submit'
                );
                ajax(url, settings);
            });

        } else if (this.data.status == 'submitted') {
            button.text("Fetch Feedback");
            button.click(function (e) {
                var settings = {
                    cache : false,
                    data : {
                        course_id: that.data.course_id,
                        History_id: that.data.History_id
                    },
                    type : "POST",
                    dataType : "json",
                    success : $.proxy(that.on_refresh, that),
                    error : function (xhr, status, error) {
                        container.empty().text("Error fetching feedback.");
                        utils.log_ajax_error(xhr, status, error);
                    }
                };
                button.text('Fetching Feedback...');
                button.attr('disabled', 'disabled');
                var url = utils.url_path_join(
                    that.base_url,
                    'Historys',
                    'fetch_feedback'
                );
                ajax(url, settings);
            });
        }

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
