require(["jquery","underscore","views/Base","splunkjs/mvc","splunkjs/mvc/tableview","splunkjs/mvc/simplexml/ready!","views/shared/PopTart"],function(__WEBPACK_EXTERNAL_MODULE_1__,__WEBPACK_EXTERNAL_MODULE_2__,__WEBPACK_EXTERNAL_MODULE_11__,__WEBPACK_EXTERNAL_MODULE_3__,__WEBPACK_EXTERNAL_MODULE_4__,__WEBPACK_EXTERNAL_MODULE_5__,__WEBPACK_EXTERNAL_MODULE_24__){return function(modules){function __webpack_require__(moduleId){if(installedModules[moduleId])return installedModules[moduleId].exports;var module=installedModules[moduleId]={exports:{},id:moduleId,loaded:!1};return modules[moduleId].call(module.exports,module,module.exports,__webpack_require__),module.loaded=!0,module.exports}var installedModules={};return __webpack_require__.m=modules,__webpack_require__.c=installedModules,__webpack_require__.p="",__webpack_require__(0)}({0:function(module,exports,__webpack_require__){var __WEBPACK_AMD_DEFINE_ARRAY__,__WEBPACK_AMD_DEFINE_RESULT__;__WEBPACK_AMD_DEFINE_ARRAY__=[__webpack_require__(1),__webpack_require__(2),__webpack_require__("splunk_monitoring_console-views/instances/components/Action"),__webpack_require__(3),__webpack_require__(4),__webpack_require__(5)],__WEBPACK_AMD_DEFINE_RESULT__=function($,_,ActionView,mvc,TableView){var TABLE_NAMES=["drilldown_indexing_rate","drilldown_queue_fill_ratio","drilldown_page_fault","drilldown_lock_time","drilldown_network_traffic","drilldown_mapped_memory_ratio","drilldown_rep_latency","drilldown_primary_oplog_window","drilldown_background_flush","drilldown_search_concurrency","drilldown_resource_usage","drilldown_load_average","drilldown_cpu_usage","drilldown_memory_usage","drilldown_disk_usage","drilldown_iostats"],initCellRender=function(tableView){var ActionCellRenderer=TableView.BaseCellRenderer.extend({canRender:function(cell){return"Action"===cell.field},render:function($td,cell){var actionValues=cell.value.split(" "),instance=actionValues[0],instanceRoles=actionValues.slice(1),searchManagerID=tableView.settings.get("managerid"),actionCell=new ActionView({instance:instance,earliest:mvc.Components.get(searchManagerID).settings.get("earliest_time"),latest:mvc.Components.get(searchManagerID).settings.get("latest_time"),roles:instanceRoles});actionCell.render().$el.appendTo($td)}});tableView.table.addCellRenderer(new ActionCellRenderer)};_.each(TABLE_NAMES,function(tableName){var table=mvc.Components.get(tableName);table&&table.getVisualization(function(tableView){initCellRender(tableView),tableView.table.render()})})}.apply(exports,__WEBPACK_AMD_DEFINE_ARRAY__),!(void 0!==__WEBPACK_AMD_DEFINE_RESULT__&&(module.exports=__WEBPACK_AMD_DEFINE_RESULT__))},1:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_1__},2:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_2__},"splunk_monitoring_console-views/instances/components/Action":function(module,exports,__webpack_require__){var __WEBPACK_AMD_DEFINE_ARRAY__,__WEBPACK_AMD_DEFINE_RESULT__;__WEBPACK_AMD_DEFINE_ARRAY__=[__webpack_require__(1),module,__webpack_require__(11),__webpack_require__("splunk_monitoring_console-views/instances/components/ViewMenu")],__WEBPACK_AMD_DEFINE_RESULT__=function($,module,BaseView,ViewMenu){return BaseView.extend({moduleId:module.id,initialize:function(){BaseView.prototype.initialize.apply(this,arguments),this.children.viewMenu=new ViewMenu({instance:this.options.instance,earliest:this.options.earliest,latest:this.options.latest,roles:this.options.roles})},events:{"mousedown .dmc-view-menu":"toggleViewMenu","mouseup .dmc-view-menu":function(e){e.preventDefault()}},toggleViewMenu:function(e){e.preventDefault(),this.children.viewMenu.show($(e.target))},render:function(){this.$el.html(this.compiledTemplate()),this.children.viewMenu.render().$el.appendTo($("body"))},template:'<div class="dmc-action-cell"><a class="dmc-view-menu" href="#"><%= _("Views").t() %><span class="caret"></span></a></div>'})}.apply(exports,__WEBPACK_AMD_DEFINE_ARRAY__),!(void 0!==__WEBPACK_AMD_DEFINE_RESULT__&&(module.exports=__WEBPACK_AMD_DEFINE_RESULT__))},11:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_11__},"splunk_monitoring_console-views/instances/components/ViewMenu":function(module,exports,__webpack_require__){var __WEBPACK_AMD_DEFINE_ARRAY__,__WEBPACK_AMD_DEFINE_RESULT__;__WEBPACK_AMD_DEFINE_ARRAY__=[__webpack_require__(1),module,__webpack_require__(24)],__WEBPACK_AMD_DEFINE_RESULT__=function($,module,PopTart){return PopTart.extend({moduleId:module.id,events:{"click .dmc-custom-drilldown-action":"onClickMenuItem"},onClickMenuItem:function(e){e.preventDefault(),this.hide(),window.open($(e.target).data("target"),"_blank")},render:function(){return this.$el.html(this.compiledTemplate({instance:this.options.instance,earliest:this.options.earliest,latest:this.options.latest,roles:this.options.roles})),this},template:'<div class="dropdown-menu dropdown-menu-narrow dmc-dropdown-menu popdown-dialog-body popdown-dialog-padded"><div class="arrow"></div><ul><li style="<%= _.contains(roles, "dmc_group_indexer") || _.contains(roles, "indexer") ? "" : "display: none" %>"><a href="#" class="dmc-custom-drilldown-action" data-target="indexing_performance_instance?form.splunk_server=<%= instance %>&form.time.earliest=<%= earliest %>&form.time.latest=<%= latest %>"><%= _("Indexing Performance").t() %></a></li><li><a href="#" class="dmc-custom-drilldown-action" data-target="resource_usage_instance?form.splunk_server=<%= instance %>&form.time.earliest=<%= earliest %>&form.time.latest=<%= latest %>"><%= _("Resource Usage").t() %></a></li><li style="<%= _.contains(roles, "dmc_group_indexer") || _.contains(roles, "dmc_group_search_head") || _.contains(roles, "indexer") || _.contains(roles, "search_head") ? "" : "display: none" %>"><a href="#" class="dmc-custom-drilldown-action" data-target="search_activity_instance?form.splunk_server=<%= instance %>&form.time.earliest=<%= earliest %>&form.time.latest=<%= latest %>&form.dmc_group=*&form.role=<%= (_.contains(roles, "dmc_group_indexer") || _.contains(roles, "indexer")) ? "dmc_group_indexer" : "dmc_group_search_head" %>"><%= _("Search Activity").t() %></a></li><li style="<%= _.contains(roles, "dmc_group_search_head") || _.contains(roles, "search_head") ? "" : "display: none" %>"><a href="#" class="dmc-custom-drilldown-action" data-target="search_usage_statistics_instance?form.splunk_server=<%= instance %>&form.time.earliest=<%= earliest %>&form.time.latest=<%= latest %>"><%= _("Search Usage Statistics").t() %></a></li><li style="<%= _.contains(roles, "dmc_group_kv_store") || _.contains(roles, "kv_store") ? "" : "display: none" %>"><a href="#" class="dmc-custom-drilldown-action" data-target="kv_store_instance?form.splunk_server=<%= instance %>&form.time.earliest=<%= earliest %>&form.time.latest=<%= latest %>"><%= _("KV Store").t() %></a></li></ul></div>'})}.apply(exports,__WEBPACK_AMD_DEFINE_ARRAY__),!(void 0!==__WEBPACK_AMD_DEFINE_RESULT__&&(module.exports=__WEBPACK_AMD_DEFINE_RESULT__))},3:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_3__},4:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_4__},5:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_5__},24:function(module,exports){module.exports=__WEBPACK_EXTERNAL_MODULE_24__}})});