// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

define([
    'base/js/namespace',
    'jquery',
    'base/js/utils',
    'base/js/dialog',
    './sorttable',
], function(Jupyter, $, utils, dialog, sorttable) {
    "use strict";
    var ajax = utils.ajax || $.ajax;
    console.log(ajax);

    console.log(sorttable);
    console.log(sorttable.Sorttable);

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
        $('.history-collapsable-link').each(function(index, el) {
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
        var len = this.data.assignments.length;
        title_text += ' ' + len + ' assignments';
        var id = this.escape_id() + '_history_box';
        this.element = $(element);

        var title = $('<h3/>')
            .text(title_text);

        title.addClass('history-collapsable-link');

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

        //children.append($('<div/>').addClass('list_item row'));
        this.assignment_data.actions.sort(function(a,b) {
            return a.timestamp - b.timestamp;
        });
        var element = $('<table>')
            .attr("id", this.assignment_data.assignment_code)
            .attr("style", "width:100%")
            .addClass('sortable')
            .append($('<thead>')
                .append($('<tr>')
                    .append($('<th>')
                        .attr("style", "width:33%")
                        .text('Timestamp')
                    )
                    .append($('<th>')
                        .attr("style", "width:33%")
                        .text('Action')
                    )
                    .append($('<th>')
                        .attr("style", "width:33%")
                        .text('User')
                    )
                )
            );
        
        for (var i=0; i<this.assignment_data.actions.length; i++) {
            //if (this.assignment_data.actions[i].user == this.userId) {
                var action_timestamp = this.assignment_data.actions[i].timestamp.replace(/\.\d+$/, '')
                var action_text = this.assignment_data.actions[i].action.replace('AssignmentActions.', '');

                if (i === 0) {
                element.find('thead')
                    .after($('<tbody/>'))
                        .after($('<tr/>')
                            .append($('<td/>')
                                .text(action_timestamp))
                            .append($('<td/>')
                                .text(action_text))
                            .append($('<td/>')
                                .text(this.assignment_data.actions[i].user)));
                } else {
                    element.find('tbody')
                        .after($('<tr/>')
                            .append($('<td/>')
                                .text(action_timestamp))
                            .append($('<td/>')
                                .text(action_text))
                            .append($('<td/>')
                                .text(this.assignment_data.actions[i].user)));
                }

            //}
        }
        sorttable.Sorttable.makeSortable(element);
        children.append(element);
        this.assignment_element.empty().append(row).append(children);
    };

    History.prototype.make_link = function () {
        var container = $('<span/>').addClass('item_name col-sm-6');

        var id = this.escape_id();
        var link = $('<a/>')
            .addClass("collapsed history-collapsable-link")
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

        /*
    SortTable
    version 2
    7th April 2007
    Stuart Langridge, http://www.kryogenix.org/code/browser/sorttable/

    Instructions:
    Download this file
    Add <script src="sorttable.js"></script> to your HTML
    Add class="sortable" to any table you'd like to make sortable
    Click on the headers to sort

    Thanks to many, many people for contributions and suggestions.
    Licenced as X11: http://www.kryogenix.org/code/browser/licence.html
    This basically means: do what you want with it.
    */


    var stIsIE = /*@cc_on!@*/false;

    sorttable = {
    init: function() {
        // quit if this function has already been called
        if (arguments.callee.done) return;
        // flag this function so we don't do the same thing twice
        arguments.callee.done = true;
        // kill the timer
        if (_timer) clearInterval(_timer);

        if (!document.createElement || !document.getElementsByTagName) return;

        sorttable.DATE_RE = /^(\d\d?)[\/\.-](\d\d?)[\/\.-]((\d\d)?\d\d)$/;

        forEach(document.getElementsByTagName('table'), function(table) {
        if (table.className.search(/\bsortable\b/) != -1) {
            sorttable.makeSortable(table);
        }
        });

    },

    makeSortable: function(table) {
        if (table.getElementsByTagName('thead').length == 0) {
        // table doesn't have a tHead. Since it should have, create one and
        // put the first table row in it.
        the = document.createElement('thead');
        the.appendChild(table.rows[0]);
        table.insertBefore(the,table.firstChild);
        }
        // Safari doesn't support table.tHead, sigh
        if (table.tHead == null) table.tHead = table.getElementsByTagName('thead')[0];

        if (table.tHead.rows.length != 1) return; // can't cope with two header rows

        // Sorttable v1 put rows with a class of "sortbottom" at the bottom (as
        // "total" rows, for example). This is B&R, since what you're supposed
        // to do is put them in a tfoot. So, if there are sortbottom rows,
        // for backwards compatibility, move them to tfoot (creating it if needed).
        sortbottomrows = [];
        for (var i=0; i<table.rows.length; i++) {
        if (table.rows[i].className.search(/\bsortbottom\b/) != -1) {
            sortbottomrows[sortbottomrows.length] = table.rows[i];
        }
        }
        if (sortbottomrows) {
        if (table.tFoot == null) {
            // table doesn't have a tfoot. Create one.
            tfo = document.createElement('tfoot');
            table.appendChild(tfo);
        }
        for (var i=0; i<sortbottomrows.length; i++) {
            tfo.appendChild(sortbottomrows[i]);
        }
        delete sortbottomrows;
        }

        // work through each column and calculate its type
        headrow = table.tHead.rows[0].cells;
        for (var i=0; i<headrow.length; i++) {
        // manually override the type with a sorttable_type attribute
        if (!headrow[i].className.match(/\bsorttable_nosort\b/)) { // skip this col
            mtch = headrow[i].className.match(/\bsorttable_([a-z0-9]+)\b/);
            if (mtch) { override = mtch[1]; }
            if (mtch && typeof sorttable["sort_"+override] == 'function') {
                headrow[i].sorttable_sortfunction = sorttable["sort_"+override];
            } else {
                headrow[i].sorttable_sortfunction = sorttable.guessType(table,i);
            }
            // make it clickable to sort
            headrow[i].sorttable_columnindex = i;
            headrow[i].sorttable_tbody = table.tBodies[0];
            dean_addEvent(headrow[i],"click", sorttable.innerSortFunction = function(e) {

            if (this.className.search(/\bsorttable_sorted\b/) != -1) {
                // if we're already sorted by this column, just
                // reverse the table, which is quicker
                sorttable.reverse(this.sorttable_tbody);
                this.className = this.className.replace('sorttable_sorted',
                                                        'sorttable_sorted_reverse');
                this.removeChild(document.getElementById('sorttable_sortfwdind'));
                sortrevind = document.createElement('span');
                sortrevind.id = "sorttable_sortrevind";
                sortrevind.innerHTML = stIsIE ? '&nbsp<font face="webdings">5</font>' : '&nbsp;&#x25B4;';
                this.appendChild(sortrevind);
                return;
            }
            if (this.className.search(/\bsorttable_sorted_reverse\b/) != -1) {
                // if we're already sorted by this column in reverse, just
                // re-reverse the table, which is quicker
                sorttable.reverse(this.sorttable_tbody);
                this.className = this.className.replace('sorttable_sorted_reverse',
                                                        'sorttable_sorted');
                this.removeChild(document.getElementById('sorttable_sortrevind'));
                sortfwdind = document.createElement('span');
                sortfwdind.id = "sorttable_sortfwdind";
                sortfwdind.innerHTML = stIsIE ? '&nbsp<font face="webdings">6</font>' : '&nbsp;&#x25BE;';
                this.appendChild(sortfwdind);
                return;
            }

            // remove sorttable_sorted classes
            theadrow = this.parentNode;
            forEach(theadrow.childNodes, function(cell) {
                if (cell.nodeType == 1) { // an element
                cell.className = cell.className.replace('sorttable_sorted_reverse','');
                cell.className = cell.className.replace('sorttable_sorted','');
                }
            });
            sortfwdind = document.getElementById('sorttable_sortfwdind');
            if (sortfwdind) { sortfwdind.parentNode.removeChild(sortfwdind); }
            sortrevind = document.getElementById('sorttable_sortrevind');
            if (sortrevind) { sortrevind.parentNode.removeChild(sortrevind); }

            this.className += ' sorttable_sorted';
            sortfwdind = document.createElement('span');
            sortfwdind.id = "sorttable_sortfwdind";
            sortfwdind.innerHTML = stIsIE ? '&nbsp<font face="webdings">6</font>' : '&nbsp;&#x25BE;';
            this.appendChild(sortfwdind);

                // build an array to sort. This is a Schwartzian transform thing,
                // i.e., we "decorate" each row with the actual sort key,
                // sort based on the sort keys, and then put the rows back in order
                // which is a lot faster because you only do getInnerText once per row
                row_array = [];
                col = this.sorttable_columnindex;
                rows = this.sorttable_tbody.rows;
                for (var j=0; j<rows.length; j++) {
                row_array[row_array.length] = [sorttable.getInnerText(rows[j].cells[col]), rows[j]];
                }
                /* If you want a stable sort, uncomment the following line */
                //sorttable.shaker_sort(row_array, this.sorttable_sortfunction);
                /* and comment out this one */
                row_array.sort(this.sorttable_sortfunction);

                tb = this.sorttable_tbody;
                for (var j=0; j<row_array.length; j++) {
                tb.appendChild(row_array[j][1]);
                }

                delete row_array;
            });
            }
        }
    },

    guessType: function(table, column) {
        // guess the type of a column based on its first non-blank row
        sortfn = sorttable.sort_alpha;
        for (var i=0; i<table.tBodies[0].rows.length; i++) {
        text = sorttable.getInnerText(table.tBodies[0].rows[i].cells[column]);
        if (text != '') {
            if (text.match(/^-?[�$�]?[\d,.]+%?$/)) {
            return sorttable.sort_numeric;
            }
            // check for a date: dd/mm/yyyy or dd/mm/yy
            // can have / or . or - as separator
            // can be mm/dd as well
            possdate = text.match(sorttable.DATE_RE)
            if (possdate) {
            // looks like a date
            first = parseInt(possdate[1]);
            second = parseInt(possdate[2]);
            if (first > 12) {
                // definitely dd/mm
                return sorttable.sort_ddmm;
            } else if (second > 12) {
                return sorttable.sort_mmdd;
            } else {
                // looks like a date, but we can't tell which, so assume
                // that it's dd/mm (English imperialism!) and keep looking
                sortfn = sorttable.sort_ddmm;
            }
            }
        }
        }
        return sortfn;
    },

    getInnerText: function(node) {
        // gets the text we want to use for sorting for a cell.
        // strips leading and trailing whitespace.
        // this is *not* a generic getInnerText function; it's special to sorttable.
        // for example, you can override the cell text with a customkey attribute.
        // it also gets .value for <input> fields.

        if (!node) return "";

        hasInputs = (typeof node.getElementsByTagName == 'function') &&
                    node.getElementsByTagName('input').length;

        if (node.getAttribute("sorttable_customkey") != null) {
        return node.getAttribute("sorttable_customkey");
        }
        else if (typeof node.textContent != 'undefined' && !hasInputs) {
        return node.textContent.replace(/^\s+|\s+$/g, '');
        }
        else if (typeof node.innerText != 'undefined' && !hasInputs) {
        return node.innerText.replace(/^\s+|\s+$/g, '');
        }
        else if (typeof node.text != 'undefined' && !hasInputs) {
        return node.text.replace(/^\s+|\s+$/g, '');
        }
        else {
        switch (node.nodeType) {
            case 3:
            if (node.nodeName.toLowerCase() == 'input') {
                return node.value.replace(/^\s+|\s+$/g, '');
            }
            case 4:
            return node.nodeValue.replace(/^\s+|\s+$/g, '');
            break;
            case 1:
            case 11:
            var innerText = '';
            for (var i = 0; i < node.childNodes.length; i++) {
                innerText += sorttable.getInnerText(node.childNodes[i]);
            }
            return innerText.replace(/^\s+|\s+$/g, '');
            break;
            default:
            return '';
        }
        }
    },

    reverse: function(tbody) {
        // reverse the rows in a tbody
        newrows = [];
        for (var i=0; i<tbody.rows.length; i++) {
        newrows[newrows.length] = tbody.rows[i];
        }
        for (var i=newrows.length-1; i>=0; i--) {
        tbody.appendChild(newrows[i]);
        }
        delete newrows;
    },

    /* sort functions
        each sort function takes two parameters, a and b
        you are comparing a[0] and b[0] */
    sort_numeric: function(a,b) {
        aa = parseFloat(a[0].replace(/[^0-9.-]/g,''));
        if (isNaN(aa)) aa = 0;
        bb = parseFloat(b[0].replace(/[^0-9.-]/g,''));
        if (isNaN(bb)) bb = 0;
        return aa-bb;
    },
    sort_alpha: function(a,b) {
        if (a[0]==b[0]) return 0;
        if (a[0]<b[0]) return -1;
        return 1;
    },
    sort_ddmm: function(a,b) {
        mtch = a[0].match(sorttable.DATE_RE);
        y = mtch[3]; m = mtch[2]; d = mtch[1];
        if (m.length == 1) m = '0'+m;
        if (d.length == 1) d = '0'+d;
        dt1 = y+m+d;
        mtch = b[0].match(sorttable.DATE_RE);
        y = mtch[3]; m = mtch[2]; d = mtch[1];
        if (m.length == 1) m = '0'+m;
        if (d.length == 1) d = '0'+d;
        dt2 = y+m+d;
        if (dt1==dt2) return 0;
        if (dt1<dt2) return -1;
        return 1;
    },
    sort_mmdd: function(a,b) {
        mtch = a[0].match(sorttable.DATE_RE);
        y = mtch[3]; d = mtch[2]; m = mtch[1];
        if (m.length == 1) m = '0'+m;
        if (d.length == 1) d = '0'+d;
        dt1 = y+m+d;
        mtch = b[0].match(sorttable.DATE_RE);
        y = mtch[3]; d = mtch[2]; m = mtch[1];
        if (m.length == 1) m = '0'+m;
        if (d.length == 1) d = '0'+d;
        dt2 = y+m+d;
        if (dt1==dt2) return 0;
        if (dt1<dt2) return -1;
        return 1;
    },

    shaker_sort: function(list, comp_func) {
        // A stable sort function to allow multi-level sorting of data
        // see: http://en.wikipedia.org/wiki/Cocktail_sort
        // thanks to Joseph Nahmias
        var b = 0;
        var t = list.length - 1;
        var swap = true;

        while(swap) {
            swap = false;
            for(var i = b; i < t; ++i) {
                if ( comp_func(list[i], list[i+1]) > 0 ) {
                    var q = list[i]; list[i] = list[i+1]; list[i+1] = q;
                    swap = true;
                }
            } // for
            t--;

            if (!swap) break;

            for(var i = t; i > b; --i) {
                if ( comp_func(list[i], list[i-1]) < 0 ) {
                    var q = list[i]; list[i] = list[i-1]; list[i-1] = q;
                    swap = true;
                }
            } // for
            b++;

        } // while(swap)
    }
    }

    /* ******************************************************************
    Supporting functions: bundled here to avoid depending on a library
    ****************************************************************** */

    // Dean Edwards/Matthias Miller/John Resig

    /* for Mozilla/Opera9 */
    if (document.addEventListener) {
        document.addEventListener("DOMContentLoaded", sorttable.init, false);
    }

    /* for Internet Explorer */
    /*@cc_on @*/
    /*@if (@_win32)
        document.write("<script id=__ie_onload defer src=javascript:void(0)><\/script>");
        var script = document.getElementById("__ie_onload");
        script.onreadystatechange = function() {
            if (this.readyState == "complete") {
                sorttable.init(); // call the onload handler
            }
        };
    /*@end @*/

    /* for Safari */
    if (/WebKit/i.test(navigator.userAgent)) { // sniff
        var _timer = setInterval(function() {
            if (/loaded|complete/.test(document.readyState)) {
                sorttable.init(); // call the onload handler
            }
        }, 10);
    }

    /* for other browsers */
    window.onload = sorttable.init;

    // written by Dean Edwards, 2005
    // with input from Tino Zijdel, Matthias Miller, Diego Perini

    // http://dean.edwards.name/weblog/2005/10/add-event/

    function dean_addEvent(element, type, handler) {
        if (element.addEventListener) {
            element.addEventListener(type, handler, false);
        } else {
            // assign each event handler a unique ID
            if (!handler.$$guid) handler.$$guid = dean_addEvent.guid++;
            // create a hash table of event types for the element
            if (!element.events) element.events = {};
            // create a hash table of event handlers for each element/event pair
            var handlers = element.events[type];
            if (!handlers) {
                handlers = element.events[type] = {};
                // store the existing event handler (if there is one)
                if (element["on" + type]) {
                    handlers[0] = element["on" + type];
                }
            }
            // store the event handler in the hash table
            handlers[handler.$$guid] = handler;
            // assign a global event handler to do all the work
            element["on" + type] = handleEvent;
        }
    };
    // a counter used to create unique IDs
    dean_addEvent.guid = 1;

    function removeEvent(element, type, handler) {
        if (element.removeEventListener) {
            element.removeEventListener(type, handler, false);
        } else {
            // delete the event handler from the hash table
            if (element.events && element.events[type]) {
                delete element.events[type][handler.$$guid];
            }
        }
    };

    function handleEvent(event) {
        var returnValue = true;
        // grab the event object (IE uses a global event object)
        event = event || fixEvent(((this.ownerDocument || this.document || this).parentWindow || window).event);
        // get a reference to the hash table of event handlers
        var handlers = this.events[event.type];
        // execute each event handler
        for (var i in handlers) {
            this.$$handleEvent = handlers[i];
            if (this.$$handleEvent(event) === false) {
                returnValue = false;
            }
        }
        return returnValue;
    };

    function fixEvent(event) {
        // add W3C standard event methods
        event.preventDefault = fixEvent.preventDefault;
        event.stopPropagation = fixEvent.stopPropagation;
        return event;
    };
    fixEvent.preventDefault = function() {
        this.returnValue = false;
    };
    fixEvent.stopPropagation = function() {
    this.cancelBubble = true;
    }

    // Dean's forEach: http://dean.edwards.name/base/forEach.js
    /*
        forEach, version 1.0
        Copyright 2006, Dean Edwards
        License: http://www.opensource.org/licenses/mit-license.php
    */

    // array-like enumeration
    if (!Array.forEach) { // mozilla already supports this
        Array.forEach = function(array, block, context) {
            for (var i = 0; i < array.length; i++) {
                block.call(context, array[i], i, array);
            }
        };
    }

    // generic enumeration
    Function.prototype.forEach = function(object, block, context) {
        for (var key in object) {
            if (typeof this.prototype[key] == "undefined") {
                block.call(context, object[key], key, object);
            }
        }
    };

    // character enumeration
    String.forEach = function(string, block, context) {
        Array.forEach(string.split(""), function(chr, index) {
            block.call(context, chr, index, string);
        });
    };

    // globally resolve forEach enumeration
    var forEach = function(object, block, context) {
        if (object) {
            var resolve = Object; // default
            if (object instanceof Function) {
                // functions have a "length" property
                resolve = Function;
            } else if (object.forEach instanceof Function) {
                // the object implements a custom forEach method so use that
                object.forEach(block, context);
                return;
            } else if (typeof object == "string") {
                // the object is a string
                resolve = String;
            } else if (typeof object.length == "number") {
                // the object is array-like
                resolve = Array;
            }
            resolve.forEach(object, block, context);
        }
    };



    return {
        'Course' : Course,
        'CourseList': CourseList,
        'History': History,
    };
});
