var django = {
  "jQuery": jQuery.noConflict(true)
};
var jQuery = django.jQuery;
var $ = jQuery;

String.prototype.format = function () {
  var formatted = this;
  for (var arg in arguments) {
    formatted = formatted.replace("{" + arg + "}", arguments[arg]);
  }
  return formatted;
};

(function ($) {
  $(function () {
    $(document).ready(function () {
      // Initialize event listeners
      ru.stalla.seeker.init_events();
    });
  });
})(django.jQuery);

var ru = (function ($, ru) {
  "use strict";

  ru.stalla.seeker = (function ($, config) {
    // Define variables for ru.stalla.seeker here
    var loc_example = "",
        loc_vscrolling = 0,
        loc_progr = [],         // Progress tracking
        loc_urlStore = "",      // Keep track of URL to be shown
        loc_goldlink_td = null, // Where the goldlink selection should go
        loc_goldlink = {},      // Store one or more goldlinks
        loc_divErr = "stalla_err",
        loc_sWaiting = " <span class=\"glyphicon glyphicon-refresh glyphicon-refresh-animate\"></span>",
        KEYS = {
          BACKSPACE: 8, TAB: 9, ENTER: 13, SHIFT: 16, CTRL: 17, ALT: 18, ESC: 27, SPACE: 32, PAGE_UP: 33, PAGE_DOWN: 34,
          END: 35, HOME: 36, LEFT: 37, UP: 38, RIGHT: 39, DOWN: 40, DELETE: 46
        },
        lAddTableRow = [
          { "table": "manu_search", "prefix": "manu", "counter": false, "events": ru.stalla.init_typeahead },
          { "table": "gedi_formset", "prefix": "gedi", "counter": false, "events": ru.stalla.init_typeahead,
            "select2_options": { "templateSelection": ru.stalla.litref_template }
          },
        ];


    // Private methods specification
    var private_methods = {
      /**
       * methodNotVisibleFromOutside - example of a private method
       * @returns {String}
       */
      methodNotVisibleFromOutside: function () {
        return "something";
      },

      /**
       *  is_in_list
       *      whether item called sName is in list lstThis
       *
       * @param {list} lstThis
       * @param {string} sName
       * @returns {boolean}
       */
      is_in_list: function (lstThis, sName) {
        var i = 0;

        try {
          for (i = 0; i < lstThis.length; i++) {
            if (lstThis[i]['name'] === sName) {
              return true;
            }
          }
          // Failure
          return false;
        } catch (ex) {
          private_methods.errMsg("is_in_list", ex);
          return false;
        }
      },

      /**
       *  get_list_value
       *      get the value of the item called sName is in list lstThis
       *
       * @param {list} lstThis
       * @param {string} sName
       * @returns {string}
       */
      get_list_value: function (lstThis, sName) {
        var i = 0;

        try {
          for (i = 0; i < lstThis.length; i++) {
            if (lstThis[i]['name'] === sName) {
              return lstThis[i]['value'];
            }
          }
          // Failure
          return "";
        } catch (ex) {
          private_methods.errMsg("get_list_value", ex);
          return "";
        }
      },

      /**
       *  set_list_value
       *      Set the value of the item called sName is in list lstThis
       *
       * @param {list} lstThis
       * @param {string} sName
       * @param {string} sValue
       * @returns {boolean}
       */
      set_list_value: function (lstThis, sName, sValue) {
        var i = 0;

        try {
          for (i = 0; i < lstThis.length; i++) {
            if (lstThis[i]['name'] === sName) {
              lstThis[i]['value'] = sValue;
              return true;
            }
          }
          // Failure
          return false;
        } catch (ex) {
          private_methods.errMsg("set_list_value", ex);
          return false;
        }
      },

      errMsg: function (sMsg, ex, bNoCode) {
        var sHtml = "",
            bCode = true;

        // Check for nocode
        if (bNoCode !== undefined) {
          bCode = not(bNoCode);
        }
        // Replace newlines by breaks
        sMsg = sMsg.replace(/\n/g, "\n<br>");
        if (ex === undefined) {
          sHtml = "Error: " + sMsg;
        } else {
          sHtml = "Error in [" + sMsg + "]<br>" + ex.message;
        }
        sHtml = "<code>" + sHtml + "</code>";
        console.log(sHtml);
        $("#" + loc_divErr).html(sHtml);
      },

      errClear: function () {
        $("#" + loc_divErr).html("");
        loc_bExeErr = false;
      },

      mainWaitStart : function() {
        var elWait = $(".main-wait").first();
        if (elWait !== undefined && elWait !== null) {
          $(elWait).removeClass("hidden");
        }
      },

      mainWaitStop: function () {
        var elWait = $(".main-wait").first();
        if (elWait !== undefined && elWait !== null) {
          $(elWait).addClass("hidden");
        }
      },

      waitInit: function (el) {
        var elResPart = null,
            elWait = null;

        try {
          // Set waiting div
          elResPart = $(el).closest(".research_part");
          if (elResPart !== null) {
            elWait = $(elResPart).find(".research-fetch").first();
          }
          return elWait;
        } catch (ex) {
          private_methods.errMsg("waitInit", ex);
        }
      },

      waitStart: function(el) {
        if (el !== null) {
          $(el).removeClass("hidden");
        }
      },

      waitStop: function (el) {
        if (el !== null) {
          $(el).addClass("hidden");
        }
      }


    }

    // Public methods
    return {

 
      /**
       *  init_events
       *      Bind main necessary events
       *
       */
      init_events: function (sUrlShow) {
        var lHtml = [],
            elA = null,
            object_id = "",
            targetid = null,
            post_loads = [],
            options = {},
            sHtml = "";

        try {
          // 
          // Allow "Search on ENTER" from typeahead fields
          $(".alt-form-row .searching").on("keypress",
            function (evt) {
              var key = evt.which,  // Get the KEY information
                start = null,
                button = null;

              // Look for ENTER
              if (key === KEYS.ENTER) {
                targetid = $(evt.target).attr("data-target");
                if (targetid !== undefined && targetid !== "") {
                  // Copy the value to there
                  $(targetid).val($(evt.target).val());
                }
                // Find the 'Search' button
                // button = $(this).closest("form").find("a[role=button]").last();
                button = $(".search-button").first();
                // Check for the inner text
                if ($(button)[0].innerText === "Search") {
                  // Found it
                  $(button).click();
                  evt.preventDefault();
                }
              }
            });


          // See if there are any post-loads to do
          $(".post-load").each(function (idx, value) {
            var targetid = $(this);
            post_loads.push(targetid);
            // Remove the class
            $(targetid).removeClass("post-load");
          });

          // No closing of certain dropdown elements on clicking
          $(".dropdown-toggle").on({
            "click": function (event) {
              var evtarget = $(event.target);
              if ($(evtarget).closest(".nocloseonclick")) {
                $(this).data("closable", false);
              } else {
                $(this).data("closable", true);
              }
            }
          });

          // Now address all items from the list of post-load items
          post_loads.forEach(function (targetid, index) {
            var data = [],
                lst_ta = [],
                i = 0,
                targeturl = $(targetid).attr("targeturl");

            // Load this one with a GET action
            $.get(targeturl, data, function (response) {
              // Remove the class
              $(targetid).removeClass("post-load");

              // Action depends on the response
              if (response === undefined || response === null || !("status" in response)) {
                private_methods.errMsg("No status returned");
              } else {
                switch (response.status) {
                  case "ok":
                    // Show the result
                    $(targetid).html(response['html']);
                    // Call initialisation again
                    ru.stalla.seeker.init_events(sUrlShow);
                    // Handle type aheads
                    if ("typeaheads" in response) {
                      // Perform typeahead for these ones
                      ru.stalla.init_event_listeners(response.typeaheads);
                    }
                    break;
                  case "error":
                    // Show the error
                    if ('msg' in response) {
                      $(targetid).html(response.msg);
                    } else {
                      $(targetid).html("An error has occurred (passim.seeker post_loads)");
                    }
                    break;
                }
              }

            });
          });

          //options = { "templateSelection": ru.stalla.ssg_template };
          //$(".django-select2.select2-ssg").djangoSelect2(options);
          //$(".django-select2.select2-ssg").select2({
          //  templateSelection: ru.stalla.ssg_template
          //});
          //$(".django-select2.select2-ssg").on("select2:select", function (e) {
          //  var sId = $(this).val(),
          //      sText = "",
          //      sHtml = "",
          //      idx = 0,
          //      elOption = null,
          //      elRendered = null;

          //  elRendered = $(this).parent().find(".select2-selection__rendered");
          //  sHtml = $(elRendered).html();
          //  idx = sHtml.indexOf("</span>");
          //  if (idx > 0) {
          //    idx += 7;
          //    sText = sHtml.substring(idx);
          //    if (sText.length > 50) {
          //      sText = sText.substring(0, 50) + "...";
          //      sHtml = sHtml.substring(0, idx) + sText;
          //      $(elRendered).html(sHtml);
          //    }
          //  }
          //});

          // NOTE: only treat the FIRST <a> within a <tr class='add-row'>
          $("tr.add-row").each(function () {
            elA = $(this).find("a").first();
            $(elA).unbind("click");
            $(elA).click(ru.stalla.seeker.tabular_addrow);
          });
          // Bind one 'tabular_deletrow' event handler to clicking that button
          $(".delete-row").unbind("click");
          $('tr td a.delete-row').click(ru.stalla.seeker.tabular_deleterow);

          // Bind the click event to all class="ajaxform" elements
          $(".ajaxform").unbind('click').click(ru.stalla.seeker.ajaxform_click);

          $(".ms.editable a").unbind("click").click(ru.stalla.seeker.manu_edit);
          $(".srm.editable a").unbind("click").click(ru.stalla.seeker.sermo_edit);

          // Show URL if needed
          if (loc_urlStore !== undefined && loc_urlStore !== "") {
            // show it
            window.location.href = loc_urlStore;
          } else if (sUrlShow !== undefined && sUrlShow !== "") {
            // window.location.href = sUrlShow;
            // history.pushState(null, null, sUrlShow);
          }

          // Set handling of unique-field
          $("td.unique-field input").unbind("change").change(ru.stalla.seeker.unique_change);

          // Make sure typeahead is re-established
          ru.stalla.init_event_listeners();
          ru.stalla.init_typeahead();

          // Switch filters
          $(".badge.filter").unbind("click").click(ru.stalla.seeker.filter_click);

          // Make modal draggable
          $(".modal-header, modal-dragpoint").on("mousedown", function (mousedownEvt) {
            var $draggable = $(this),
                x = mousedownEvt.pageX - $draggable.offset().left,
                y = mousedownEvt.pageY - $draggable.offset().top;

            $("body").on("mousemove.draggable", function (mousemoveEvt) {
              $draggable.closest(".modal-dialog").offset({
                "left": mousemoveEvt.pageX - x,
                "top": mousemoveEvt.pageY - y
              });
            });
            $("body").one("mouseup", function () {
              $("body").off("mousemove.draggable");
            });
            $draggable.closest(".modal").one("bs.modal.hide", function () {
              $("body").off("mousemove.draggable");
            });
          });

          //// Any other draggables
          //$(".draggable").draggable({
          //  cursor: "move",
          //  snap: ".draggable",
          //  snapMode: "inner",
          //  snapTolerance: 20
          //});

         } catch (ex) {
          private_methods.errMsg("init_events", ex);
        }
      },


      /**
       * unique_change
       *    Make sure only one input box is editable
       *
       */
      init_select2: function (elName) {
        var select2_options = null,
            i = 0,
            elDiv = "#" + elName,
            oRow = null;

        try {
          for (i = 0; i < lAddTableRow.length; i++) {
            oRow = lAddTableRow[i];
            if (oRow['table'] === elName) {
              if ("select2_options" in oRow) {
                select2_options = oRow['select2_options'];
                // Remove previous .select2
                $(elDiv).find(".select2").remove();
                // Execute djangoSelect2()
                $(elDiv).find(".django-select2").djangoSelect2(select2_options);
                return true;
              }
            }
          }
          return false;
        } catch (ex) {
          private_methods.errMsg("init_select2", ex);
          return false;
        }
      },

 
      /**
       * add_new_select2
       *    Show [table_new] element
       *
       */
      add_new_select2: function (el) {
        var elTr = null,
            elRow = null,
            options = {},
            elDiv = null;

        try {
          elTr = $(el).closest("tr");           // Nearest <tr>
          elDiv = $(elTr).find(".new-mode");    // The div with new-mode in it
          // Show it
          $(elDiv).removeClass("hidden");
          // Find the first row
          elRow = $(elDiv).find("tbody tr").first();
          options['select2'] = true;
          ru.stalla.seeker.tabular_addrow($(elRow), options);

          // Add
        } catch (ex) {
          private_methods.errMsg("add_new_select2", ex);
        }
      },

      /**
       * form_row_select
       *    By selecting this slement, the whole row gets into the 'selected' state
       *
       */
      form_row_select: function (elStart) {
        var elTable = null,
          elRow = null, // The row
          iSelCount = 0, // Number of selected rows
          elHier = null,
          bSelected = false;

        try {
          // Get to the row
          elRow = $(elStart).closest("tr.form-row");
          // Get current state
          bSelected = $(elRow).hasClass("selected");
          // FInd nearest table
          elTable = $(elRow).closest("table");
          // Check if anything other than me is selected
          iSelCount = 1;
          // Remove all selection
          $(elTable).find(".form-row.selected").removeClass("selected");
          elHier = $("#sermon_hierarchy");
          // CHeck what we need to do
          if (bSelected) {
            // We are de-selecting: hide the 'Up' and 'Down' buttons if needed
            // ru.cesar.seeker.show_up_down(this, false);
            $(elHier).removeClass("in");
            $(elHier).hide()
          } else {
            // Make a copy of the tree as it is
            $("#sermon_tree_copy").html($("#sermon_tree").html());
            // Select the new row
            $(elRow).addClass("selected");
            // SHow the 'Up' and 'Down' buttons if needed
            // ru.cesar.seeker.show_up_down(this, true);
            // document.getElementById('sermon_manipulate').submit();
            $(elHier).addClass("in");
            $(elHier).show();
          }

        } catch (ex) {
          private_methods.errMsg("form_row_select", ex);
        }
      },


      /**
       * search_reset
       *    Clear the information in the form's fields and then do a submit
       *
       */
      search_reset: function (elStart) {
        var frm = null;

        try {
          // Get to the form
          frm = $(elStart).closest('form');
          // Clear the information in the form's INPUT fields
          $(frm).find("input:not([readonly]).searching").val("");
          // Show we are waiting
          $("#waitingsign").removeClass("hidden");
          // Now submit the form
          frm.submit();
        } catch (ex) {
          private_methods.errMsg("search_reset", ex);
        }
      },

      /**
       * search_clear
       *    No real searching, just reset the criteria
       *
       */
      search_clear: function (elStart) {
        var frm = null,
            idx = 0,
            lFormRow = [];

        try {
          // Clear filters
          $(".badge.filter").each(function (idx, elThis) {
            var target;

            target = $(elThis).attr("targetid");
            if (target !== undefined && target !== null && target !== "") {
              target = $("#" + target);
              // Action depends on checking or not
              if ($(elThis).hasClass("on")) {
                // it is on, switch it off
                $(elThis).removeClass("on");
                $(elThis).removeClass("jumbo-3");
                $(elThis).addClass("jumbo-1");
                // Must hide it and reset target
                $(target).addClass("hidden");
                $(target).find("input").each(function (idx, elThis) {
                  $(elThis).val("");
                });
                // Also reset all select 2 items
                $(target).find("select").each(function (idx, elThis) {
                  $(elThis).val("").trigger("change");
                });
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("search_clear", ex);
        }
      },

      /**
       * search_start
       *    Gather the information in the form's fields and then do a submit
       *
       */
      search_start: function (elStart, method, iPage, sOrder) {
        var frm = null,
            url = "",
            targetid = null,
            targeturl = "",
            data = null;

        try {
          // Get to the form
          frm = $(elStart).closest('form');
          // Get the data from the form
          data = frm.serializeArray();

          // Determine the method
          if (method === undefined) { method = "submit";}

          // Get the URL from the form
          url = $(frm).attr("action");

          // Action depends on the method
          switch (method) {
            case "submit":
              // Show we are waiting
              $("#waitingsign").removeClass("hidden");
              // Store the current URL
              loc_urlStore = url;
              // If there is a page number, we need to process it
              if (iPage !== undefined) {
                $(elStart).find("input[name=page]").each(function (el) {
                  $(this).val(iPage);
                });
              }
              // If there is a sort order, we need to process it
              if (sOrder !== undefined) {
                $(elStart).find("input[name=o]").each(function (el) {
                  $(this).val(sOrder);
                });
              }
              // Now submit the form
              frm.submit();
              break;
            case "post":
              // Determine the targetid
              targetid = $(elStart).attr("targetid");
              if (targetid == "subform") {
                targetid = $(elStart).closest(".subform");
              } else {
                targetid = $("#" + targetid);
              }
              // Get the targeturl
              targeturl = $(elStart).attr("targeturl");

              // Get the page we need to go to
              if (iPage === undefined) { iPage = 1; }
              data.push({ 'name': 'page', 'value': iPage });
              if (sOrder !== undefined) {
                data.push({ 'name': 'o', 'value': sOrder });
              }

              // Issue a post
              $.post(targeturl, data, function (response) {
                // Action depends on the response
                if (response === undefined || response === null || !("status" in response)) {
                  private_methods.errMsg("No status returned");
                } else {
                  switch (response.status) {
                    case "ready":
                    case "ok":
                      // Show the HTML target
                      $(targetid).html(response['html']);
                      // Possibly do some initialisations again??

                      // Make sure events are re-established
                      // ru.stalla.seeker.init_events();
                      ru.stalla.init_typeahead();
                      break;
                    case "error":
                      // Show the error
                      if ('msg' in response) {
                        $(targetid).html(response.msg);
                      } else {
                        $(targetid).html("An error has occurred (passim.seeker search_start)");
                      }
                      break;
                  }
                }
              });


              break;
          }

        } catch (ex) {
          private_methods.errMsg("search_start", ex);
        }
      },

      /**
       * search_paged_start
       *    Perform a simple 'submit' call to search_start
       *
       */
      search_paged_start: function(iPage) {
        var elStart = null;

        try {
          // And then go to the first element within the form that is of any use
          elStart = $(".search_paged_start").first();
          ru.stalla.seeker.search_start(elStart, 'submit', iPage)
        } catch (ex) {
          private_methods.errMsg("search_paged_start", ex);
        }
      },

      /**
       * search_ordered_start
       *    Perform a simple 'submit' call to search_start
       *
       */
      search_ordered_start: function (order) {
        var elStart = null;

        try {
          // And then go to the first element within the form that is of any use
          elStart = $(".search_ordered_start").first();
          ru.stalla.seeker.search_start(elStart, 'submit', 1, order)
        } catch (ex) {
          private_methods.errMsg("search_ordered_start", ex);
        }
      },


      /**
       * check_progress
       *    Check the progress of reading e.g. codices
       *
       */
      check_progress: function (progrurl, sTargetDiv) {
        var elTarget = "#" + sTargetDiv,
            sMsg = "",
            lHtml = [];

        try {
          $(elTarget).removeClass("hidden");
          // Call the URL
          $.get(progrurl, function (response) {
            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ready":
                case "finished":
                  // NO NEED for further action
                  //// Indicate we are ready
                  //$(elTarget).html("READY");
                  break;
                case "error":
                  // Show the error
                  if ('msg' in response) {
                    $(elTarget).html(response.msg);
                  } else {
                    $(elTarget).html("An error has occurred (passim.seeker check_progress)");
                  }                  
                  break;
                default:
                  if ("msg" in response) { sMsg = response.msg; }
                  // Combine the status
                  sMsg = "<tr><td>" + response.status + "</td><td>" + sMsg + "</td></tr>";
                  // Check if it is on the stack already
                  if ($.inArray(sMsg, loc_progr) < 0) {
                    loc_progr.push(sMsg);
                  }
                  // Combine the status HTML
                  sMsg = "<div style=\"max-height: 200px; overflow-y: scroll;\"><table>" + loc_progr.reverse().join("\n") + "</table></div>";
                  $(elTarget).html(sMsg);
                  // Make sure we check again
                  window.setTimeout(function () { ru.stalla.seeker.check_progress(progrurl, sTargetDiv); }, 200);
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("check_progress", ex);
        }
      },

      /**
       * hide
       *   Hide element [sHide] and 
       *
       */
      hide: function (sHide) {
        try {
          $("#" + sHide).addClass("hidden");
        } catch (ex) {
          private_methods.errMsg("hide", ex);
        }
      },

      /**
       * select_row
       *   Select one row in a table
       *
       */
      select_row: function (elStart, method, id) {
        var tbl = null,
            elsubform = null,
            eltowards = null,
            sSermon = "",
            select_id = "";

        try {
          // Get the table
          tbl = $(elStart).closest("table");
          // Deselect all other rows
          $(tbl).children("tbody").children("tr").removeClass("selected");
          // Select my current row
          $(elStart).addClass("selected");

          // Determine the select id: the id of the selected target
          if (id !== undefined && id !== "") {
            select_id = id;
          }

          // Determine the element in [sermongoldlink_info.html] where we need to change something
          elsubform = $(elStart).closest("div .subform");
          if (elsubform !== null && elsubform !== undefined) {
            eltowards = $(elsubform).attr("towardsid");
            if (eltowards === undefined) {
              eltowards = null;
            } else {
              eltowards = $("#" + eltowards);
            }
          }

          // Action depends on the method
          switch (method) {
            case "gold_link":
              // Select the correct gold sermon above
              if (eltowards !== null && $(eltowards).length > 0) {
                // Set the text of this sermon
                sSermon = $(elStart).find("td").last().html();
                $(eltowards).find(".edit-mode").first().html(sSermon);

                // Set the id of this sermon
                // DOESN'T EXIST!!! $(eltowards).find("#id_glink-dst").val(select_id.toString());
              }
              break;
          }
        } catch (ex) {
          private_methods.errMsg("select_row", ex);
        }
      },

      /**
       * import_data
       *   Allow user to upload a file
       *
       * Assumptions:
       * - the [el] contains parameter  @targeturl
       * - there is a div 'import_progress'
       * - there is a div 'id_{{ftype}}-{{forloop.counter0}}-file_source'
       *   or one for multiple files: 'id_files_field'
       *
       */
      import_data: function (sKey) {
        var frm = null,
            targeturl = "",
            options = {},
            fdata = null,
            el = null,
            elProg = null,    // Progress div
            elErr = null,     // Error div
            progrurl = null,  // Any progress function to be called
            data = null,
            xhr = null,
            files = null,
            sFtype = "",      // Type of function (cvar, feat, cond)
            elWait = null,
            bDoLoad = false,  // Need to load with a $.get() afterwards
            elInput = null,   // The <input> element with the files
            more = {},        // Additional (json) data to be passed on (from form-data)
            sTargetDiv = "",  // The div where the uploaded reaction comes
            sSaveDiv = "",    // Where to go if saving is needed
            sMsg = "";

        try {
          // The element to use is the key + import_info
          el = $("#" + sKey + "-import_info");
          elProg = $("#" + sKey + "-import_progress");
          elErr = $("#" + sKey + "-import_error");

          // Set the <div> to be used for waiting
          elWait = private_methods.waitInit(el);

          // Get the URL
          targeturl = $(el).attr("targeturl");
          progrurl = $(el).attr("sync-progress");
          sTargetDiv = $(el).attr("targetid");
          sSaveDiv = $(el).attr("saveid");

          if (targeturl === undefined && sSaveDiv !== undefined && sSaveDiv !== "") {
            targeturl = $("#" + sSaveDiv).attr("ajaxurl");
            sTargetDiv = $("#" + sSaveDiv).attr("openid");
            sFtype = $(el).attr("ftype");
            bDoLoad = true;
          }

          if ($(el).is("input")) {
            elInput = el;
          } else {
            elInput = $(el).find("input").first();
          }

          // Show progress
          $(elProg).attr("value", "0");
          $(elProg).removeClass("hidden");
          if (bDoLoad) {
            $(".save-warning").html("loading the definition..." + loc_sWaiting);
            $(".submit-row button").prop("disabled", true);
          }

          // Add data from the <form> nearest to me: 
          frm = $(el).closest("form");
          if (frm !== undefined) { data = $(frm).serializeArray(); }

          for (var i = 0; i < data.length; i++) {
            more[data[i]['name']] = data[i]['value'];
          }
          // Showe the user needs to wait...
          private_methods.waitStart(elWait);

          // Now initiate any possible progress calling
          if (progrurl !== null) {
            loc_progr = [];
            window.setTimeout(function () { ru.stalla.seeker.check_progress(progrurl, sTargetDiv); }, 2000);
          }

          // Upload XHR
          $(elInput).upload(targeturl,
            more,
            function (response) {
              // Transactions have been uploaded...
              console.log("done: ", response);

              // Show where we are
              $(el).addClass("hidden");
              $(".save-warning").html("saving..." + loc_sWaiting);

              // First leg has been done
              if (response === undefined || response === null || !("status" in response)) {
                private_methods.errMsg("No status returned");
              } else {
                switch (response.status) {
                  case "ok":
                    // Check how we should react now
                    if (bDoLoad) {
                      // Show where we are
                      $(".save-warning").html("retrieving..." + loc_sWaiting);

                      $.get(targeturl, function (response) {
                        if (response === undefined || response === null || !("status" in response)) {
                          private_methods.errMsg("No status returned");
                        } else {
                          switch (response.status) {
                            case "ok":
                              // Show the response in the appropriate location
                              $("#" + sTargetDiv).html(response.html);
                              $("#" + sTargetDiv).removeClass("hidden");
                              break;
                            default:
                              // Check how/what to show
                              if ("err_view" in response) {
                                private_methods.errMsg(response['err_view']);
                              } else if ("error_list" in response) {
                                private_methods.errMsg(response['error_list']);
                              } else {
                                // Just show the HTML
                                $("#" + sTargetDiv).html(response.html);
                                $("#" + sTargetDiv).removeClass("hidden");
                              }
                              break;
                          }
                          // Make sure events are in place again
                          ru.stalla.seeker.init_events();
                          switch (sFtype) {
                            case "cvar":
                              ru.stalla.seeker.init_cvar_events();
                              break;
                            case "cond":
                              ru.stalla.seeker.init_cond_events();
                              break;
                            case "feat":
                              ru.stalla.seeker.init_feat_events();
                              break;
                          }
                          // Indicate we are through with waiting
                          private_methods.waitStop(elWait);
                        }
                      });
                    } else {
                      // Remove all project-part class items
                      $(".project-part").addClass("hidden");
                      // Place the response here
                      $("#" + sTargetDiv).html(response.html);
                      $("#" + sTargetDiv).removeClass("hidden");
                    }
                    break;
                  default:
                    // Check WHAT to show
                    sMsg = "General error (unspecified)";
                    if ("err_view" in response) {
                      sMsg = response['err_view'];
                    } else if ("error_list" in response) {
                      sMsg = response['error_list'];
                    } else {
                      // Indicate that the status is not okay
                      sMsg = "Status is not good. It is: " + response.status;
                    }
                    // Show the message at the appropriate location
                    $(elErr).html("<div class='error'>" + sMsg + "</div>");
                    // Make sure events are in place again
                    ru.stalla.seeker.init_events();
                    switch (sFtype) {
                      case "cvar":
                        ru.stalla.seeker.init_cvar_events();
                        break;
                      case "cond":
                        ru.stalla.seeker.init_cond_events();
                        break;
                      case "feat":
                        ru.stalla.seeker.init_feat_events();
                        break;
                    }
                    // Indicate we are through with waiting
                    private_methods.waitStop(elWait);
                    $(".save-warning").html("(not saved)");
                    break;
                }
              }
              private_methods.waitStop(elWait);
            }, function (progress, value) {
              // Show  progress of uploading to the user
              console.log(progress);
              $(elProg).val(value);
            }
          );
          // Hide progress after some time
          setTimeout(function () { $(elProg).addClass("hidden"); }, 1000);

          // Indicate waiting can stop
          private_methods.waitStop(elWait);
        } catch (ex) {
          private_methods.errMsg("import_data", ex);
          private_methods.waitStop(elWait);
        }
      },

      stop_bubbling: function(event) {
        event.handled = true;
        return false;
      },


 
      /**
       * formset_setdel
       *   Set the delete checkbox of me
       *
       */
      formset_setdel: function (elStart) {

        try {
          // Set the delete value of the checkbox
          $(elStart).closest("td").find("input[type=checkbox]").first().prop("checked", true);
        } catch (ex) {
          private_methods.errMsg("formset_setdel", ex);
        }
      },

      /**
       * formset_update
       *   Send an Ajax POST request and process the response in a standard way
       *
       */
      formset_update: function (elStart, sAction) {
        var targetid = "",
            err = "#error_location",
            errdiv = null,
            waitclass = ".formset-wait",
            elWaitRow = null,
            data = [],
            lHtml = [],
            i = 0,
            frm = null,
            targeturl = "";

        try {
          // Get the correct error div
          errdiv = $(elStart).closest("form").find(err).first();
          if (errdiv === undefined || errdiv === null) {
            errdiv = $(err);
          }

          // Get attributes
          targetid = $(elStart).attr("targetid");
          targeturl = $(elStart).attr("targeturl");

          // Possibly set delete flag
          if (sAction !== undefined && sAction !== "") {
            switch (sAction) {
              case "delete":
                // Set the delete value of the checkbox
                $(elStart).closest("td").find("input[type=checkbox]").first().prop("checked", true);
                break;
              case "wait":
                // Set a waiting thing at the targetid
                $("#" + targetid).html(loc_sWaiting);
                // Make sure the caller is inactivated
                $(elStart).addClass("hidden");
                break;
            }
          }

          // Check if there is a waiting row
          elWaitRow = $(elStart).closest("table").find(waitclass);
          if (elWaitRow.length > 0) { $(elWaitRow).removeClass('hidden');}

          // Gather the data
          frm = $(elStart).closest("form");
          data = $(frm).serializeArray();
          data = jQuery.grep(data, function (item) {
            return (item['value'].indexOf("__counter__") < 0 && item['value'].indexOf("__prefix__") < 0);
          });
          $.post(targeturl, data, function (response) {
            // Show we have a response
            if (elWaitRow.length > 0) { $(elWaitRow).addClass('hidden'); }

            // Action depends on the response
            if (response === undefined || response === null || !("status" in response)) {
              private_methods.errMsg("No status returned");
            } else {
              switch (response.status) {
                case "ready":
                case "ok":
                case "error":
                  if ("html" in response) {
                    // If there is an error, indicate this
                    if (response.status === "error") {
                      if ("msg" in response) {
                        if (typeof response['msg'] === "object") {
                          lHtml = []
                          lHtml.push("Errors:");
                          $.each(response['msg'], function (key, value) { lHtml.push(key + ": " + value); });
                          $(errdiv).html(lHtml.join("<br />"));
                        } else {
                          $(errdiv).html("Error: " + response['msg']);
                        }
                      } else if ('error_list' in response) {
                        lHtml = []
                        lHtml.push("Errors:");
                        for (i = 0; i < response['error_list'].length; i++) {
                          lHtml.push(response['error_list'][i]);
                        }
                        $(errdiv).html(lHtml.join("<br />"));
                      } else {
                        $(errdiv).html("<code>There is an error</code>");
                      }
                      $(errdiv).removeClass("hidden");
                    } else {
                      // Show the HTML in the targetid
                      $("#" + targetid).html(response['html']);
                      // Action...
                      if (sAction !== undefined && sAction !== "") {
                        switch (sAction) {
                          case "wait":
                            $(elStart.removeClass("hidden"));
                            break;
                        }
                      }
                      // Check for other specific matters
                      switch (targetid) {
                        case "sermongold_eqset":
                          // We need to update 'sermongold_linkset'
                          ru.stalla.seeker.do_get("sermongold_linkset");
                          break;
                        case "sermon_linkset":
                          // We need to update 'sermongold_ediset'
                          ru.stalla.seeker.do_get("sermondescr_ediset");
                          break;
                      }
                    }
                    // But make sure events are back on again
                    ru.stalla.seeker.init_events();
                  } else {
                    // Send a message
                    $(errdiv).html("<i>There is no <code>html</code> in the response from the server</i>");
                  }
                  break;
                default:
                  // Something went wrong -- show the page or not?
                  $(errdiv).html("The status returned is unknown: " + response.status);
                  break;
              }
            }
          });

        } catch (ex) {
          private_methods.errMsg("formset_update", ex);
        }
      },

      /**
       * tabular_deleterow
       *   Delete one row from a tabular inline
       *
       */
      tabular_deleterow: function () {
        var sId = "",
            elDiv = null,
            elRow = null,
            elPrev = null,
            elDel = null,   // The delete inbox
            sPrefix = "",
            elForms = "",
            counter = $(this).attr("counter"),
            deleteurl = "",
            data = [],
            frm = null,
            bCounter = false,
            bHideOnDelete = false,
            iForms = 0,
            prefix = "simplerel",
            use_prev_row = false,   // Delete the previous row instead of the current one
            bValidated = false;

        try {
          // Get the prefix, if possible
          sPrefix = $(this).attr("extra");
          bCounter = (typeof counter !== typeof undefined && counter !== false && counter !== "");
          elForms = "#id_" + sPrefix + "-TOTAL_FORMS"
          // Find out just where we are
          elDiv = $(this).closest("div[id]")
          sId = $(elDiv).attr("id");
          // Find out how many forms there are right now
          iForms = $(elForms).val();
          frm = $(this).closest("form");
          // The validation action depends on this id
          switch (sId) {
            // gold
            case "glink_formset":
            case "gedi_formset":
            case "gftxt_formset":
            case "gsign_formset":
            case "gkw_formset":
            case "gcol_formset":
            // super
            case "scol_formset":
            case "ssglink_formset":
            // sermo 
            case "stog_formset":
            case "sdsignformset":
            case "sdcol_formset":
            case "sdkw_formset":
            // manu
            case "mprov_formset":
            case "mdr_formset":
            case "mkw_formset":
            case "mcol_formset":
            case "manu_search":
              //// Indicate that deep evaluation is needed
              //if (!confirm("Do you really want to remove this gold sermon? (All links to and from this gold sermon will also be removed)")) {
              //  // Return from here
              //  return;
              //}
              use_prev_row = false;
              bValidated = true;
              break;
          }
          // Continue with deletion only if validated
          if (bValidated) {
            // Get the deleteurl (if existing)
            deleteurl = $(this).attr("targeturl");
            // Get to the row
            if (use_prev_row) {
              // Delete both the current and the previous row
              elRow = $(this).closest("tr");
              elPrev = $(elRow).prev();
              $(elRow).remove();
              $(elPrev).remove();
            } else {
              // Only delete the current row
              elRow = $(this).closest("tr");
              // Do we need to hide or delete?
              if ($(elRow).hasClass("hide-on-delete")) {
                bHideOnDelete = true;
                $(elRow).addClass("hidden");
              } else {
                $(elRow).remove();
              }
            }

            // Further action depends on whether the row just needs to be hidden
            if (bHideOnDelete) {
              // Row has been hidden: now find and set the DELETE checkbox
              elDel = $(elRow).find("input:checkbox[name$='DELETE']");
              if (elDel !== null) {
                $(elDel).prop("checked", true);
              }
            } else {
              // Decrease the amount of forms
              iForms -= 1;
              $(elForms).val(iForms);

              // Re-do the numbering of the forms that are shown
              $(elDiv).find(".form-row").not(".empty-form").each(function (idx, elThisRow) {
                var iCounter = 0, sRowId = "", arRowId = [];

                iCounter = idx + 1;
                // Adapt the ID attribute -- if it EXISTS
                sRowId = $(elThisRow).attr("id");
                if (sRowId !== undefined) {
                  arRowId = sRowId.split("-");
                  arRowId[1] = idx;
                  sRowId = arRowId.join("-");
                  $(elThisRow).attr("id", sRowId);
                }

                if (bCounter) {
                  // Adjust the number in the FIRST <td>
                  $(elThisRow).find("td").first().html(iCounter.toString());
                }

                // Adjust the numbering of the INPUT and SELECT in this row
                $(elThisRow).find("input, select").each(function (j, elInput) {
                  // Adapt the name of this input
                  var sName = $(elInput).attr("name");
                  if (sName !== undefined) {
                    var arName = sName.split("-");
                    arName[1] = idx;
                    sName = arName.join("-");
                    $(elInput).attr("name", sName);
                    $(elInput).attr("id", "id_" + sName);
                  }
                });
              });
            }

            // The validation action depends on this id (or on the prefix)
            switch (sId) {
              case "search_mode_simple":
                // Update -- NOTE: THIS IS A LEFT-OVER FROM CESAR
                ru.stalla.seeker.simple_update();
                break;
              case "ssglink_formset":
                if (deleteurl !== undefined &&  deleteurl !== "") {
                  // prepare data
                  data = $(frm).serializeArray();
                  data.push({ 'name': 'action', 'value': 'delete' });
                  $.post(deleteurl, data, function (response) {
                    // Action depends on the response
                    if (response === undefined || response === null || !("status" in response)) {
                      private_methods.errMsg("No status returned");
                    } else {
                      switch (response.status) {
                        case "ready":
                        case "ok":
                          // Refresh the current page
                          window.location = window.location;
                          break;
                        case "error":
                          // Show the error
                          if ('msg' in response) {
                            $(targetid).html(response.msg);
                          } else {
                            $(targetid).html("An error has occurred (passim.seeker tabular_deleterow)");
                          }
                          break;
                      }
                    }
                  });
                }
                break;
            }
          }

        } catch (ex) {
          private_methods.errMsg("tabular_deleterow", ex);
        }
      },

      /**
       * tabular_addrow
       *   Add one row into a tabular inline
       *
       */
      tabular_addrow: function (elStart, options) {
        // NOTE: see the definition of lAddTableRow above
        var arTdef = lAddTableRow,
            oTdef = {},
            rowNew = null,
            elTable = null,
            select2_options = {},
            iNum = 0,     // Number of <tr class=form-row> (excluding the empty form)
            sId = "",
            bSelect2 = false,
            i;

        try {
          // Find out just where we are
          if (elStart === undefined || elStart === null || $(elStart).closest("div").length === 0)
            elStart = $(this);
          sId = $(elStart).closest("div[id]").attr("id");
          // Process options
          if (options !== undefined) {
            for (var prop in options) {
              switch (prop) {
                case "select2": bSelect2 = options[prop]; break;
              }
            }
          } else {
            options = $(elStart).attr("options");
            if (options !== undefined && options === "select2") {
              bSelect2 = true;
            }
          }
          // Walk all tables
          for (i = 0; i < arTdef.length; i++) {
            // Get the definition
            oTdef = arTdef[i];
            if (sId === oTdef.table || sId.indexOf(oTdef.table) >= 0) {
              // Go to the <tbody> and find the last form-row
              elTable = $(elStart).closest("tbody").children("tr.form-row.empty-form")

              if ("select2_options" in oTdef) {
                select2_options = oTdef.select2_options;
              }

              // Perform the cloneMore function to this <tr>
              rowNew = ru.stalla.seeker.cloneMore(elTable, oTdef.prefix, oTdef.counter);
              // Call the event initialisation again
              if (oTdef.events !== null) {
                oTdef.events();
              }
              // Possible Select2 follow-up
              if (bSelect2) {
                // Remove previous .select2
                $(rowNew).find(".select2").remove();
                // Execute djangoSelect2()
                $(rowNew).find(".django-select2").djangoSelect2(select2_options);
              }
              // Any follow-up activity
              if ('follow' in oTdef && oTdef['follow'] !== null) {
                oTdef.follow(rowNew);
              }
              // We are done...
              break;
            }
          }
        } catch (ex) {
          private_methods.errMsg("tabular_addrow", ex);
        }
      },

      /**
       *  cloneMore
       *      Add a form to the formset
       *      selector = the element that should be duplicated
       *      type     = the formset type
       *      number   = boolean indicating that re-numbering on the first <td> must be done
       *
       */
      cloneMore: function (selector, type, number) {
        var elTotalForms = null,
            total = 0;

        try {
          // Clone the element in [selector]
          var newElement = $(selector).clone(true);
          // Find the total number of [type] elements
          elTotalForms = $('#id_' + type + '-TOTAL_FORMS').first();
          // Determine the total of already available forms
          if (elTotalForms === null || elTotalForms.length ===0) {
            // There is no TOTAL_FORMS for this type, so calculate myself
          } else {
            // Just copy the TOTAL_FORMS value
            total = parseInt($(elTotalForms).val(), 10);
          }

          // Find each <input> element
          newElement.find(':input').each(function (idx, el) {
            var name = "",
                id = "",
                val = "",
                td = null;

            if ($(el).attr("name") !== undefined) {
              // Get the name of this element, adapting it on the fly
              name = $(el).attr("name").replace("__prefix__", total.toString());
              // Produce a new id for this element
              id = $(el).attr("id").replace("__prefix__", total.toString());
              // Adapt this element's name and id, unchecking it
              $(el).attr({ 'name': name, 'id': id }).val('').removeAttr('checked');
              // Possibly set a default value
              td = $(el).parent('td');
              if (td.length === 0) {
                td = $(el).parent("div").parent("td");
              }
              if (td.length === 1) {
                val = $(td).attr("defaultvalue");
                if (val !== undefined && val !== "") {
                  $(el).val(val);
                }
              }
            }
          });
          newElement.find('select').each(function (idx, el) {
            var td = null;

            if ($(el).attr("name") !== undefined) {
              td = $(el).parent('td');
              if (td.length === 0) { td = $(el).parent("div").parent("td"); }
              if (td.length === 0 || (td.length === 1 && $(td).attr("defaultvalue") === undefined)) {
                // Get the name of this element, adapting it on the fly
                var name = $(el).attr("name").replace("__prefix__", total.toString());
                // Produce a new id for this element
                var id = $(el).attr("id").replace("__prefix__", total.toString());
                // Adapt this element's name and id, unchecking it
                $(el).attr({ 'name': name, 'id': id }).val('').removeAttr('checked');
              }
            }
          });

          // Find each <label> under newElement
          newElement.find('label').each(function (idx, el) {
            if ($(el).attr("for") !== undefined) {
              // Adapt the 'for' attribute
              var newFor = $(el).attr("for").replace("__prefix__", total.toString());
              $(el).attr('for', newFor);
            }
          });

          // Look at the inner text of <td>
          newElement.find('td').each(function (idx, el) {
            var elInsideTd = $(el).find("td");
            var elText = $(el).children().first();
            if (elInsideTd.length === 0 && elText !== undefined) {
              var sHtml = $(elText).html();
              if (sHtml !== undefined && sHtml !== "") {
                sHtml = sHtml.replace("__counter__", (total+1).toString());
                $(elText).html(sHtml);
              }
              // $(elText).html($(elText).html().replace("__counter__", total.toString()));
            }
          });
          // Look at the attributes of <a> and of <input>
          newElement.find('a, input').each(function (idx, el) {
            // Iterate over all attributes
            var elA = el;
            $.each(elA.attributes, function (i, attrib) {
              var attrText = $(elA).attr(attrib.name).replace("__counter__", total.toString());
              // EK (20/feb): $(this).attr(attrib.name, attrText);
              $(elA).attr(attrib.name, attrText);
            });
          });


          // Adapt the total number of forms in this formset
          total++;
          $('#id_' + type + '-TOTAL_FORMS').val(total);

          // Adaptations on the new <tr> itself
          newElement.attr("id", "arguments-" + (total - 1).toString());
          newElement.attr("class", "form-row row" + total.toString());

          // Insert the new element before the selector = empty-form
          $(selector).before(newElement);

          // Should we re-number?
          if (number !== undefined && number) {
            // Walk all <tr> elements of the table
            var iRow = 1;
            $(selector).closest("tbody").children("tr.form-row").not(".empty-form").each(function (idx, el) {
              var elFirstCell = $(el).find("td").not(".hidden").first();
              $(elFirstCell).html(iRow);
              iRow += 1;
            });
          }

          // Return the new <tr> 
          return newElement;

        } catch (ex) {
          private_methods.errMsg("cloneMore", ex);
          return null;
        }
      },

      /**
       * toggle_click
       *   Action when user clicks an element that requires toggling a target
       *
       */
      toggle_click: function (elThis, class_to_close) {
        var elGroup = null,
            elTarget = null,
            sStatus = "";

        try {
          // Get the target to be opened
          elTarget = $(elThis).attr("targetid");
          // Sanity check
          if (elTarget !== null) {
            // Show it if needed
            if ($("#" + elTarget).hasClass("hidden")) {
              $("#" + elTarget).removeClass("hidden");
            } else {
              $("#" + elTarget).addClass("hidden");
              // Check if there is an additional class to close
              if (class_to_close !== undefined && class_to_close !== "") {
                $("." + class_to_close).addClass("hidden");
              }
            }
          }
        } catch (ex) {
          private_methods.errMsg("toggle_click", ex);
        }
      },

    };
  }($, ru.config));

  return ru;
}(jQuery, window.ru || {})); // window.ru: see http://stackoverflow.com/questions/21507964/jslint-out-of-scope

